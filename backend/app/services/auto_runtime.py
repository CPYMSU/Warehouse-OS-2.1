"""Shared goal-driven Auto Runtime for every Warehouse OS AI surface.

This is deliberately the only model-facing boundary.  Surfaces may supply a
different interaction format, but they cannot select commands, invoke SQL, or
maintain a separate tool loop.  Domain capability execution will be connected
here as typed adapters mature; until then the runtime stays explicit about
what it has observed and never claims an unperformed business action.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.config import Settings
from app.db.session import tenant_session
from app.services.confirmation_actions import (
    execute_authorized_confirmation_action,
    propose_confirmation_action,
)
from app.services.conversation_history import recent_conversation_context
from app.services.integrations import (
    DEEPSEEK_RUNTIME_MODELS,
    ModelConnection,
    chat_completion,
    connected_deepseek,
)
from app.services.integrations import httpx as httpx
from app.services.language_contract import (
    language_instruction,
    localized_empty_answer,
    localized_empty_plan,
    localized_structure_failure,
    message_matches_locale,
    normalize_locale,
    resolve_language_contract,
)
from app.services.memory_fabric import build_memory_capsule
from app.services.overview import executive_overview_payload
from app.services.runtime_context import (
    build_router_context,
    expand_capability_domains,
    expand_selected_capabilities,
    hydrate_company_authority,
    hydrate_experience_memory,
    hydrate_hosting_world,
    hydrate_recent_context,
    responsibility_for_genes,
)
from app.services.runtime_output import public_message as _public_message
from app.services.runtime_output import public_plan_steps as _public_plan_steps
from app.services.warehouse_operations import bootstrap_warehouse_payload
from app.templates.industry_blueprints import BLUEPRINT_PERMISSION_KEYS
from app.terminal.catalog import (
    ai_capability_atlas,
    ai_capability_candidates,
    ai_capability_gene_index,
    ai_capability_genes,
    entry_by_tool_name,
)
from app.terminal.executor import execute_runtime_tool_call

if TYPE_CHECKING:
    from app.api.deps import ActorContext


_MAX_AUTONOMOUS_ROUNDS = 4
_MAX_AUTONOMOUS_TOOL_CALLS = 16
_MAX_CONTINUATION_DECISIONS = 8


_ABSOLUTE_RESOURCE_LOCATOR = re.compile(r"https?://[^\s<>\"'`]+", re.IGNORECASE)
_MARKDOWN_RESOURCE_LOCATOR = re.compile(r"\]\((/[^)\s]+)\)")
_ROOT_RESOURCE_LOCATOR = re.compile(
    r"(?<![A-Za-z0-9_])(/(?!/)(?:[A-Za-z0-9._~%+-]+/)+"
    r"[A-Za-z0-9._~%?=&+#-]*)"
)
_LOCATOR_TRAILING_PUNCTUATION = ".,;:!?。，；：！？)]}"


RuntimeActivityCallback = Callable[[dict[str, object]], None]


def _emit_activity(
    callback: RuntimeActivityCallback | None,
    **payload: object,
) -> None:
    """Publish a bounded, non-sensitive execution state without affecting work."""
    if callback is None:
        return
    try:
        callback(dict(payload))
    except Exception:
        # Observability is never allowed to change an operational outcome.
        return


@dataclass(frozen=True)
class RuntimeResult:
    """A surface-neutral turn result with observable cognitive phases."""

    goal: str
    message: str
    model: str
    observations: dict[str, object]
    plan: tuple[str, ...]
    run_id: str | None = None
    distillation: dict[str, object] = field(default_factory=dict)
    decisions: tuple[dict[str, object], ...] = ()
    tool_results: tuple[dict[str, object], ...] = ()
    credentials: tuple[dict[str, object], ...] = ()
    downloads: tuple[dict[str, object], ...] = ()
    confirmation_actions: tuple[dict[str, object], ...] = ()
    reflection: dict[str, object] = field(default_factory=dict)
    response_locale: str = "zh-Hant"


def _safe_download_markers(result: object) -> tuple[dict[str, object], ...]:
    """Extract bounded, same-origin downloads from one command envelope."""

    if not isinstance(result, dict):
        return ()
    candidates: list[object] = []
    for container in (result, result.get("data")):
        if isinstance(container, dict) and isinstance(container.get("downloads"), list):
            candidates.extend(container["downloads"])
    downloads: list[dict[str, object]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        url = str(candidate.get("url") or "").strip()
        label = str(candidate.get("label") or "下載").strip()[:160]
        filename = str(candidate.get("filename") or "download").strip()[:180]
        if (
            not url.startswith("/api/")
            or "\r" in url
            or "\n" in url
            or ".." in url.split("?", 1)[0].split("/")
            or "/" in filename
            or "\\" in filename
            or url in seen
        ):
            continue
        seen.add(url)
        downloads.append({"label": label or "下載", "url": url, "filename": filename})
        if len(downloads) >= 12:
            break
    return tuple(downloads)


def _resource_locators(value: object) -> tuple[str, ...]:
    """Extract exact resource locators without assigning business meaning.

    Locators are protocol-level values.  The Runtime may reason freely about a
    goal, but it may not manufacture a new address and present it as observed
    external reality.
    """

    found: list[str] = []
    seen: set[str] = set()

    def include(candidate: object) -> None:
        locator = str(candidate or "").rstrip(_LOCATOR_TRAILING_PUNCTUATION)
        if locator and locator not in seen:
            seen.add(locator)
            found.append(locator)

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for child in item.values():
                visit(child)
            return
        if isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
            return
        if not isinstance(item, str):
            return
        absolute_matches = list(_ABSOLUTE_RESOURCE_LOCATOR.finditer(item))
        for match in absolute_matches:
            include(match.group(0))
        for match in _MARKDOWN_RESOURCE_LOCATOR.finditer(item):
            include(match.group(1))
        for match in _ROOT_RESOURCE_LOCATOR.finditer(item):
            if any(start <= match.start() < end for start, end in (
                absolute.span() for absolute in absolute_matches
            )):
                continue
            include(match.group(1))

    visit(value)
    return tuple(found)


def _localized_grounding_gap(locale: str) -> str:
    selected = normalize_locale(locale) or "zh-Hant"
    return {
        "zh-Hant": (
            "目前的世界觀察不足以證明所要求的結果或資源位置；"
            "Runtime 已停止交付未經證實的內容，且沒有把推測當成完成結果。"
        ),
        "zh-Hans": (
            "目前的世界观察不足以证明所要求的结果或资源位置；"
            "Runtime 已停止交付未经证实的内容，也没有把推测当成完成结果。"
        ),
        "en": (
            "The current world observations do not establish the requested result or "
            "resource location. The Runtime stopped instead of presenting an inference "
            "as a completed outcome."
        ),
    }[selected]


def _language_prompt(layers: dict[str, object]) -> str:
    current_goal = layers.get("L2_current_goal")
    current_goal = current_goal if isinstance(current_goal, dict) else {}
    contract = current_goal.get("language_contract")
    contract = contract if isinstance(contract, dict) else {}
    return language_instruction(contract.get("locale"))


def _ensure_message_locale(
    connection: object,
    message: str,
    locale: str,
    metrics: list[dict[str, object]],
    *,
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> str:
    """Run one bounded repair pass only when the final prose is clearly wrong."""
    safe_message = _public_message(message, locale=locale)
    if not safe_message or message_matches_locale(safe_message, locale):
        return safe_message
    raw = _completion(
        connection,
        system_prompt=(
            "Repair only the language of the supplied user-facing message. Preserve its "
            "meaning and structure. Do not add facts. Return JSON only with one key named "
            "message. "
            + language_instruction(locale)
        ),
        user_prompt=json.dumps({"message": safe_message}, ensure_ascii=False),
        metrics=metrics,
        phase="language_repair",
        context_mode=context_mode,
        max_tokens=1_200,
        activity_callback=activity_callback,
    )
    parsed = _json_object(raw) or {}
    repaired = _public_message(
        parsed.get("message"),
        locale=locale,
        fallback=safe_message,
    )
    return (
        repaired
        if repaired and message_matches_locale(repaired, locale)
        else safe_message
    )


def runtime_capability_map() -> list[dict[str, object]]:
    """Expose a dynamic domain map distilled from the capability catalogue."""
    return [
        {
            "domain": item["domain"],
            "capability": "compose_domain_capabilities",
            "kind": item["kind"],
            "state": ("active" if int(item["active_count"]) else "adapter_pending"),
            "gene_count": item["gene_count"],
            "active_count": item["active_count"],
        }
        for item in ai_capability_atlas()
    ]


def _number(value: object, default: int | float = 0) -> int | float:
    """Normalise a persisted numeric value before it enters a UI/model snapshot."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def runtime_world_snapshot(actor: ActorContext) -> dict[str, object]:
    """Return the terminal's permission-filtered, tenant-DB-backed world view.

    The snapshot deliberately contains a small, stable set of operational
    facts instead of exposing table-shaped data or a database execution
    surface.  It is used by both the Codex-style terminal display and the
    shared Runtime's observation phase, which keeps UI and model context in
    sync while retaining the normal tenant RLS boundary.
    """
    warehouse_payload = bootstrap_warehouse_payload(actor)
    hub = warehouse_payload.get("WAREHOUSE_HUB")
    hub = hub if isinstance(hub, dict) else {}
    access = hub.get("access")
    access = access if isinstance(access, dict) else {}
    inventory = hub.get("inventory")
    inventory = inventory if isinstance(inventory, dict) else {}
    orders = hub.get("orders")
    orders = orders if isinstance(orders, dict) else {}
    shipments = hub.get("shipments")
    shipments = shipments if isinstance(shipments, dict) else {}
    overview = executive_overview_payload(actor)
    modules = overview.get("modules")
    modules = modules if isinstance(modules, dict) else {}
    audit = modules.get("audit")
    audit = audit if isinstance(audit, dict) else {}

    can_read_inventory = bool(access.get("inventory"))
    can_read_inbound = bool(access.get("inbound"))
    can_read_outbound = bool(access.get("outbound"))
    can_read_shipments = bool(access.get("shipments"))
    can_read_audit = audit.get("status") == "ready"
    attention = hub.get("attention") if can_read_inventory else []
    attention = attention if isinstance(attention, list) else []
    anomalies = hub.get("anomalies") if can_read_inventory else []
    anomalies = anomalies if isinstance(anomalies, list) else []

    return {
        "source": "tenant_postgresql",
        "scope": "permission-filtered",
        "company": {"slug": actor.tenant_slug, "name": actor.tenant_name},
        "inventory": {
            "available": can_read_inventory,
            "skus": int(_number(inventory.get("skus"))) if can_read_inventory else None,
            "low_skus": int(_number(inventory.get("low_skus"))) if can_read_inventory else None,
            "zero_skus": int(_number(inventory.get("zero_skus"))) if can_read_inventory else None,
            "stock_value": _number(inventory.get("stock_value")) if can_read_inventory else None,
        },
        "work": {
            "inbound_open": int(_number(orders.get("inbound_open"))) if can_read_inbound else None,
            "outbound_open": (
                int(_number(orders.get("outbound_open"))) if can_read_outbound else None
            ),
            "shipments_active": (
                int(_number(shipments.get("active"))) if can_read_shipments else None
            ),
            "shipments_delayed": (
                int(_number(shipments.get("delayed"))) if can_read_shipments else None
            ),
        },
        "governance": {
            "available": can_read_audit,
            "events_24h": int(_number(audit.get("writes"))) if can_read_audit else None,
            "failed_events": int(_number(audit.get("failed"))) if can_read_audit else None,
        },
        "attention": [item for item in attention[:6] if isinstance(item, dict)],
        "anomalies": [item for item in anomalies[:6] if isinstance(item, dict)],
    }


def _company_ai_actor(actor: ActorContext) -> ActorContext:
    """Project an authenticated tenant into its company-caretaker observation."""
    return replace(
        actor,
        role_level=max(10, actor.role_level),
        permissions=frozenset(BLUEPRINT_PERMISSION_KEYS),
    )


def _json_object(value: str) -> dict[str, object] | None:
    """Extract one JSON object from a model response without business inference."""
    candidate = value.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```")
        candidate = candidate.removesuffix("```").strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _completion(
    connection: object,
    *,
    system_prompt: str,
    user_prompt: str,
    metrics: list[dict[str, object]] | None = None,
    phase: str = "completion",
    context_mode: str = "balanced",
    max_tokens: int = 1_200,
    activity_callback: RuntimeActivityCallback | None = None,
) -> str:
    started = perf_counter()
    input_chars = len(system_prompt) + len(user_prompt)
    activity_id = f"model:{phase}"
    _emit_activity(
        activity_callback,
        activity_id=activity_id,
        kind="model",
        phase=phase,
        status="running",
        model=str(getattr(connection, "model", "")),
    )
    try:
        result = chat_completion(
            connection,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            thinking=context_mode == "thinking",
            max_tokens=max_tokens,
            json_mode=True,
        )
    except Exception:
        duration_ms = round((perf_counter() - started) * 1000)
        if metrics is not None:
            metrics.append(
                {
                    "phase": phase,
                    "input_chars": input_chars,
                    "estimated_input_tokens": (input_chars + 3) // 4,
                    "output_chars": 0,
                    "duration_ms": duration_ms,
                    "status": "failed",
                }
            )
        _emit_activity(
            activity_callback,
            activity_id=activity_id,
            kind="model",
            phase=phase,
            status="failed",
            model=str(getattr(connection, "model", "")),
            elapsed_ms=duration_ms,
        )
        raise
    duration_ms = round((perf_counter() - started) * 1000)
    if metrics is not None:
        metrics.append(
            {
                "phase": phase,
                "input_chars": input_chars,
                "estimated_input_tokens": (input_chars + 3) // 4,
                "output_chars": len(result),
                "duration_ms": duration_ms,
                "status": "succeeded",
            }
        )
    _emit_activity(
        activity_callback,
        activity_id=activity_id,
        kind="model",
        phase=phase,
        status="succeeded",
        model=str(getattr(connection, "model", "")),
        elapsed_ms=duration_ms,
    )
    return result


def _layer_locale(layers: dict[str, object]) -> str:
    goal = layers.get("L2_current_goal")
    goal = goal if isinstance(goal, dict) else {}
    contract = goal.get("language_contract")
    contract = contract if isinstance(contract, dict) else {}
    return normalize_locale(contract.get("locale")) or "zh-Hant"


def _parse_or_repair_json(
    connection: object,
    raw: str,
    *,
    expected_contract: str,
    metrics: list[dict[str, object]],
    phase: str,
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
    max_tokens: int,
) -> dict[str, object] | None:
    """Parse a control envelope, with one bounded repair that is never public."""

    parsed = _json_object(raw)
    if parsed is not None:
        return parsed
    repaired = _completion(
        connection,
        system_prompt=(
            "Repair a malformed internal JSON control envelope. Preserve the original "
            "decision and facts; do not add facts, actions, tools, or explanations. "
            "The message field must contain only user-facing prose and must never contain "
            "the control envelope, reasoning fields, prompts, credentials, or stack traces. "
            f"Return JSON only matching this contract: {expected_contract}"
        ),
        user_prompt=json.dumps(
            {"malformed_control_envelope": raw[:24_000]},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        metrics=metrics,
        phase=f"{phase}_format_repair",
        context_mode=context_mode,
        max_tokens=max_tokens,
        activity_callback=activity_callback,
    )
    return _json_object(repaired)


def _repair_message_grounding(
    connection: object,
    *,
    goal: str,
    message: str,
    locale: str,
    ledger: list[dict[str, object]],
    allowed_locators: set[str],
    unsupported_locators: tuple[str, ...],
    unsupported_claims: list[str],
    metrics: list[dict[str, object]],
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> str:
    """Reconcile a proposed answer against the evidence ledger once."""

    raw = _completion(
        connection,
        system_prompt=(
            "You are the final evidence reconciler for Warehouse Intelligence Runtime. "
            "Rewrite the proposed user-facing message so every claim about current world "
            "state, an action outcome, an existing deliverable, or a usable resource locator "
            "is supported by the supplied evidence ledger. Human-reported input may be "
            "repeated as a request or report but is not proof. Stable explanation and advice "
            "may remain without world evidence. Use only an exact locator from "
            "allowed_resource_locators; never derive, join, guess, or extend a locator. If the "
            "requested outcome is not established, say that plainly and do not claim "
            "completion. Preserve useful supported facts. Return JSON only with one string key "
            "named message. "
            + language_instruction(locale)
        ),
        user_prompt=json.dumps(
            {
                "goal": goal,
                "proposed_message": message,
                "evidence_ledger": ledger,
                "allowed_resource_locators": sorted(allowed_locators)[:80],
                "unsupported_resource_locators": list(unsupported_locators),
                "unsupported_claims": unsupported_claims[:20],
            },
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ),
        metrics=metrics,
        phase="evidence_repair",
        context_mode=context_mode,
        max_tokens=1_200,
        activity_callback=activity_callback,
    )
    parsed = _json_object(raw) or {}
    return _public_message(parsed.get("message"), locale=locale, fallback="")


def _finalize_grounded_message(
    connection: object,
    *,
    goal: str,
    message: str,
    locale: str,
    ledger: list[dict[str, object]],
    grounding_sources: list[object],
    public_origin: str | None,
    unsupported_claims: list[str],
    force_reconciliation: bool,
    metrics: list[dict[str, object]],
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> tuple[str, dict[str, object]]:
    """Apply exact-locator provenance after every prose transformation."""

    unsupported_locators = _unsupported_resource_locators(
        message,
        grounding_sources,
        public_origin=public_origin,
    )
    if not (unsupported_locators or unsupported_claims or force_reconciliation):
        return message, {
            "reconciled": False,
            "unsupported_resource_locators": [],
        }
    allowed = _allowed_resource_locators(
        grounding_sources,
        public_origin=public_origin,
    )
    repaired = _repair_message_grounding(
        connection,
        goal=goal,
        message=message,
        locale=locale,
        ledger=ledger,
        allowed_locators=allowed,
        unsupported_locators=unsupported_locators,
        unsupported_claims=unsupported_claims,
        metrics=metrics,
        context_mode=context_mode,
        activity_callback=activity_callback,
    )
    remaining = _unsupported_resource_locators(
        repaired,
        grounding_sources,
        public_origin=public_origin,
    )
    if not repaired or remaining or not message_matches_locale(repaired, locale):
        repaired = _localized_grounding_gap(locale)
    return repaired, {
        "reconciled": True,
        "unsupported_resource_locators": list(unsupported_locators),
        "repair_left_unsupported_resource_locators": list(remaining),
    }


def _context_metrics(phases: list[dict[str, object]]) -> dict[str, object]:
    return {
        "architecture": "hierarchical_funnel_v2",
        "model_calls": len(phases),
        "total_input_chars": sum(int(item.get("input_chars") or 0) for item in phases),
        "estimated_input_tokens": sum(
            int(item.get("estimated_input_tokens") or 0) for item in phases
        ),
        "total_duration_ms": sum(int(item.get("duration_ms") or 0) for item in phases),
        "phases": phases,
    }


def _compact_for_model(
    value: object,
    *,
    depth: int = 0,
    max_depth: int = 4,
    max_items: int = 5,
    max_keys: int = 28,
    max_string: int = 500,
) -> object:
    """Create a generic bounded evidence projection without domain rules.

    Full tool responses remain in the run record. Model phases receive a
    structural preview plus explicit omitted counts, and may request a more
    exact capability/entity in a later round.
    """
    if isinstance(value, str):
        return (
            value
            if len(value) <= max_string
            else value[:max_string] + f"…[{len(value) - max_string} chars omitted]"
        )
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if depth >= max_depth:
        if isinstance(value, dict):
            return {
                "_type": "object",
                "_keys": [str(key) for key in list(value)[:max_keys]],
                "_omitted_depth": True,
            }
        if isinstance(value, (list, tuple)):
            return {
                "_type": "array",
                "_count": len(value),
                "_omitted_depth": True,
            }
        return str(value)[:max_string]
    if isinstance(value, dict):
        pairs = list(value.items())
        projected = {
            str(key): _compact_for_model(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_keys=max_keys,
                max_string=max_string,
            )
            for key, item in pairs[:max_keys]
        }
        if len(pairs) > max_keys:
            projected["_omitted_keys"] = len(pairs) - max_keys
        return projected
    if isinstance(value, (list, tuple)):
        projected = [
            _compact_for_model(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_keys=max_keys,
                max_string=max_string,
            )
            for item in list(value)[:max_items]
        ]
        if len(value) > max_items:
            projected.append(
                {
                    "_omitted_items": len(value) - max_items,
                    "_total_items": len(value),
                }
            )
        return projected
    return str(value)[:max_string]


def _evidence_ledger(
    goal: str,
    layers: dict[str, object],
    tool_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Build a bounded, source-labelled ledger for reflective judgment.

    The ledger is intentionally domain-neutral.  It distinguishes what the
    human reported, what the tenant context currently observes, and what a
    capability returned.  The model decides what those observations mean;
    deterministic code only validates that cited evidence identifiers exist.
    """

    records: list[dict[str, object]] = [
        {
            "evidence_id": "input:goal",
            "source_type": "human_report",
            "authority": "reported_not_verified",
            "payload": _compact_for_model(goal),
        }
    ]
    l1 = layers.get("L1_current_company_and_people")
    l1 = l1 if isinstance(l1, dict) else {}
    for key in ("company_summary", "company_authority_world", "hosted_application_world"):
        value = l1.get(key)
        if value in (None, [], {}) or (
            isinstance(value, dict) and value.get("loaded") is False
        ):
            continue
        records.append(
            {
                "evidence_id": f"context:{key}",
                "source_type": "current_tenant_context",
                "authority": "observed",
                "payload": _compact_for_model(value),
            }
        )
    l3 = layers.get("L3_execution_working_set")
    l3 = l3 if isinstance(l3, dict) else {}
    for key in ("company_world_observation", "exact_entities", "world_observations"):
        value = l3.get(key)
        if value in (None, [], {}):
            continue
        records.append(
            {
                "evidence_id": f"context:{key}",
                "source_type": "current_tenant_context",
                "authority": "observed",
                "payload": _compact_for_model(value),
            }
        )
    for index, item in enumerate(tool_results, start=1):
        if not isinstance(item, dict):
            continue
        result = item.get("result")
        result = result if isinstance(result, dict) else {}
        evidence_id = str(
            item.get("evidence_id")
            or f"capability:{int(item.get('runtime_round') or 0)}:{index}:"
            f"{str(item.get('tool_name') or 'unknown')}"
        )
        records.append(
            {
                "evidence_id": evidence_id,
                "source_type": "capability_result",
                "authority": "observed",
                "tool_name": item.get("tool_name"),
                "status": result.get("status") or ("succeeded" if result.get("ok") else None),
                "payload": _compact_for_model(result),
            }
        )
    return records[:40]


def _grounding_source_values(
    goal: str,
    layers: dict[str, object],
    tool_results: list[dict[str, object]],
    downloads: list[dict[str, object]] | tuple[dict[str, object], ...] = (),
) -> list[object]:
    """Return raw provenance sources from which exact locators may be repeated."""

    sources: list[object] = [goal, tool_results, list(downloads)]
    l1 = layers.get("L1_current_company_and_people")
    l1 = l1 if isinstance(l1, dict) else {}
    for key in ("company_summary", "company_authority_world", "hosted_application_world"):
        value = l1.get(key)
        if value not in (None, [], {}) and not (
            isinstance(value, dict) and value.get("loaded") is False
        ):
            sources.append(value)
    l3 = layers.get("L3_execution_working_set")
    l3 = l3 if isinstance(l3, dict) else {}
    for key in ("company_world_observation", "exact_entities", "world_observations"):
        value = l3.get(key)
        if value not in (None, [], {}):
            sources.append(value)
    return sources


def _allowed_resource_locators(
    sources: list[object],
    *,
    public_origin: str | None = None,
) -> set[str]:
    allowed = set(_resource_locators(sources))
    origin = str(public_origin or "").rstrip("/")
    if origin:
        allowed.update(
            f"{origin}{locator}"
            for locator in tuple(allowed)
            if locator.startswith("/")
        )
    return allowed


def _unsupported_resource_locators(
    message: str,
    sources: list[object],
    *,
    public_origin: str | None = None,
) -> tuple[str, ...]:
    allowed = _allowed_resource_locators(sources, public_origin=public_origin)
    return tuple(
        locator for locator in _resource_locators(message) if locator not in allowed
    )


def _apply_reflection_evidence_contract(
    reflection: dict[str, object],
    *,
    interaction_mode: str,
    ledger: list[dict[str, object]],
) -> dict[str, object]:
    """Validate model evidence references and the Runtime completion boundary."""

    valid_ids = {
        str(item.get("evidence_id"))
        for item in ledger
        if isinstance(item, dict) and item.get("evidence_id")
    }
    normalized_claims: list[dict[str, object]] = []
    unsupported_claims: list[str] = []
    for item in reflection.get("claims") or []:
        if not isinstance(item, dict):
            continue
        statement = str(item.get("statement") or item.get("claim") or "").strip()[:800]
        evidence_refs = list(
            dict.fromkeys(
                str(ref)
                for ref in item.get("evidence_refs") or []
                if str(ref) in valid_ids
            )
        )[:12]
        requires_evidence = bool(item.get("requires_evidence"))
        supported = not requires_evidence or bool(evidence_refs)
        normalized_claims.append(
            {
                "statement": statement,
                "requires_evidence": requires_evidence,
                "evidence_refs": evidence_refs,
                "supported": supported,
            }
        )
        if statement and not supported:
            unsupported_claims.append(statement)

    world_evidence_ids = {
        str(item.get("evidence_id"))
        for item in ledger
        if isinstance(item, dict)
        and (
            item.get("source_type") == "capability_result"
            or str(item.get("evidence_id"))
            in {
                "context:company_authority_world",
                "context:hosted_application_world",
                "context:company_world_observation",
                "context:exact_entities",
                "context:world_observations",
            }
        )
    }
    operational_without_world_evidence = (
        str(interaction_mode).strip().lower() == "operational"
        and not world_evidence_ids
    )
    if unsupported_claims or operational_without_world_evidence:
        reflection["goal_complete"] = False
        if not reflection.get("continue_reason"):
            reflection["continue_reason"] = "world_evidence_required"
    reflection["claims"] = normalized_claims
    reflection["grounding"] = {
        "contract": "warehouse.claim-evidence.v1",
        "evidence_ids": sorted(valid_ids),
        "world_evidence_ids": sorted(world_evidence_ids),
        "unsupported_claims": unsupported_claims,
        "operational_without_world_evidence": operational_without_world_evidence,
    }
    return reflection


def _domain_index_prompt(
    domain_index: list[dict[str, object]],
    *,
    description_chars: int,
) -> dict[str, object]:
    return {
        "columns": [
            "tool_name",
            "domain",
            "family",
            "description",
            "availability",
            "mode",
        ],
        "rows": [
            [
                item.get("tool_name"),
                item.get("domain"),
                item.get("family"),
                str(item.get("description") or "")[:description_chars],
                item.get("availability"),
                item.get("mode"),
            ]
            for item in domain_index
            if isinstance(item, dict)
        ],
    }


def _parameter_contracts(tool_names: list[str]) -> list[dict[str, object]]:
    contracts: list[dict[str, object]] = []
    for gene in ai_capability_genes(tool_names):
        schema = gene.get("schema")
        schema = schema if isinstance(schema, dict) else {}
        function = schema.get("function")
        function = function if isinstance(function, dict) else {}
        name = function.get("name")
        if not name:
            continue
        contracts.append(
            {
                "tool_name": name,
                "parameters": function.get("parameters") or {},
                "confirmation_policy": gene.get("confirmation_policy") or {},
            }
        )
    return contracts


def _authority_evidence_projection(
    layers: dict[str, object],
    tool_results: list[dict[str, object]],
) -> dict[str, object]:
    """Join observed workflow references to the live tenant authority graph.

    This is a data-driven context join, not an authorization decision. The AI
    still decides whether a missing holder or position is a real blocker.
    """
    l1 = layers.get("L1_current_company_and_people")
    l1 = l1 if isinstance(l1, dict) else {}
    l2 = layers.get("L2_current_goal")
    l2 = l2 if isinstance(l2, dict) else {}
    l3 = layers.get("L3_execution_working_set")
    l3 = l3 if isinstance(l3, dict) else {}
    authority = l1.get("company_authority_world")
    if not isinstance(authority, dict):
        return {}

    permission_values: set[str] = set()
    position_values: set[str] = set()
    department_values: set[str] = set()
    position_contexts: dict[str, list[dict[str, object]]] = {}

    def visit(
        value: object,
        key: str = "",
        context: dict[str, object] | None = None,
    ) -> None:
        context = dict(context or {})
        if isinstance(value, dict):
            for context_key in ("workflow_key", "node_key", "name", "step_no"):
                context_value = value.get(context_key)
                if isinstance(context_value, (str, int, float)):
                    context[context_key] = context_value
            position_code = value.get("position_code")
            if isinstance(position_code, str) and position_code:
                row = {
                    field: context[field]
                    for field in ("workflow_key", "node_key", "name", "step_no")
                    if field in context
                }
                rows = position_contexts.setdefault(position_code, [])
                if row and row not in rows and len(rows) < 80:
                    rows.append(row)
            for child_key, child_value in value.items():
                visit(child_value, str(child_key), context)
            return
        if isinstance(value, (list, tuple)):
            for child in value:
                visit(child, key, context)
            return
        if not isinstance(value, str) or not value:
            return
        normalized_key = key.lower()
        if normalized_key in {
            "required_permission",
            "permission_key",
            "permission",
        }:
            permission_values.add(value)
        elif normalized_key.endswith("position_code"):
            position_values.add(value)
        elif normalized_key.endswith("department_code"):
            department_values.add(value)

    visit(tool_results)
    responsibility_index = authority.get("responsibility_index")
    responsibility_index = (
        responsibility_index if isinstance(responsibility_index, dict) else {}
    )
    position_rows = {
        str(item.get("code")): item
        for item in authority.get("positions") or []
        if isinstance(item, dict) and item.get("code")
    }
    department_rows = {
        str(item.get("code")): item
        for item in authority.get("departments") or []
        if isinstance(item, dict) and item.get("code")
    }
    holders_by_position: dict[str, list[str]] = {}
    for person in authority.get("people") or []:
        if not isinstance(person, dict):
            continue
        display_name = str(person.get("display_name") or person.get("username") or "")
        for identity in person.get("identities") or []:
            if not isinstance(identity, dict) or not identity.get("position_code"):
                continue
            holders_by_position.setdefault(
                str(identity["position_code"]),
                [],
            ).append(display_name)
    return {
        "observed_required_permissions": {
            permission: responsibility_index.get(
                permission,
                {"people": [], "positions": []},
            )
            for permission in sorted(permission_values)
        },
        "observed_position_references": [
            {
                "code": code,
                "exists": code in position_rows,
                "name": (
                    position_rows[code].get("name")
                    if code in position_rows
                    else None
                ),
                "active_holders": list(
                    dict.fromkeys(holders_by_position.get(code, []))
                ),
                "workflow_nodes": position_contexts.get(code, []),
            }
            for code in sorted(position_values)
        ],
        "observed_department_references": [
            {
                "code": code,
                "exists": code in department_rows,
                "name": (
                    department_rows[code].get("name")
                    if code in department_rows
                    else None
                ),
            }
            for code in sorted(department_values)
        ],
        "judgment_note": (
            "Reference existence and holders are evidence only; the model "
            "must judge whether they block the user's goal."
        ),
    }


def _reference_value_projection(
    tool_results: list[dict[str, object]],
) -> dict[str, list[object]]:
    """Distil stable identifiers/status values from full untruncated results."""
    values: dict[str, list[object]] = {}

    def include_key(key: str) -> bool:
        normalized = key.lower()
        return normalized in {
            "id",
            "name",
            "status",
            "active",
            "count",
            "total",
            "ok",
            "error",
            "reason",
        } or normalized.endswith(("_key", "_code", "_id"))

    def visit(value: object, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, str(child_key))
            return
        if isinstance(value, (list, tuple)):
            for child in value:
                visit(child, key)
            return
        if not include_key(key) or value is None:
            return
        scalar: object
        if isinstance(value, (bool, int, float)):
            scalar = value
        else:
            scalar = str(value)[:300]
        bucket = values.setdefault(key, [])
        if scalar not in bucket and len(bucket) < 80:
            bucket.append(scalar)

    visit(tool_results)
    return values


def _world_observation_projection(
    tool_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Retain domain observations as L3/L4 world evidence.

    Domain adapters may emit observations anywhere inside their normal result
    envelope.  The Runtime does not interpret them as a workflow; it preserves
    canonical entities, verified facts, uncertainty and affordances for the
    model's next subjective judgment.
    """

    observations: list[dict[str, object]] = []
    seen: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if value.get("schema") == "warehouse.world-observation.v1":
                canonical = json.dumps(
                    value,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
                if canonical not in seen and len(observations) < 80:
                    seen.add(canonical)
                    observations.append(dict(value))
            for child in value.values():
                visit(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)

    visit(tool_results)
    return observations


def _atomic_recovery_projection(
    tool_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Keep generic recovery affordances visible after any capability failure."""

    packets: list[dict[str, object]] = []
    seen: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if value.get("schema") == "warehouse.atomic-recovery.v1":
                canonical = json.dumps(
                    value,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
                if canonical not in seen and len(packets) < 40:
                    seen.add(canonical)
                    packets.append(dict(value))
            for child in value.values():
                visit(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)

    visit(tool_results)
    return packets


def _conversation_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _start_run(
    actor: ActorContext,
    *,
    run_id: UUID,
    conversation_id: str | None,
    goal: str,
    layers: dict[str, object],
) -> None:
    conversation_uuid = _conversation_uuid(conversation_id)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO secretariat.runs(
                  id, tenant_id, conversation_id, actor_user_id, task, status,
                  context_snapshot
                ) VALUES (
                  :id, :tenant_id,
                  (SELECT id FROM secretariat.conversations
                   WHERE id = :conversation_id LIMIT 1),
                  :actor_user_id, :task, 'running', CAST(:context AS jsonb)
                )
                """
            ),
            {
                "id": run_id,
                "tenant_id": actor.tenant_id,
                "conversation_id": conversation_uuid,
                "actor_user_id": actor.user_id,
                "task": goal,
                "context": json.dumps(
                    {
                        "architecture": "hierarchical_funnel_v2",
                        "layers": layers,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        )


def _finish_run(
    actor: ActorContext,
    *,
    run_id: UUID,
    status: str,
    snapshot: dict[str, object],
) -> None:
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE secretariat.runs
                SET status = :status, context_snapshot = CAST(:snapshot AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "status": status,
                "snapshot": json.dumps(snapshot, ensure_ascii=False, default=str),
            },
        )


def _persist_memory_candidate(
    actor: ActorContext,
    *,
    run_id: UUID,
    candidate: object,
) -> str | None:
    """Persist a model-proposed private memory with auditable run evidence."""
    if not isinstance(candidate, dict):
        return None
    kind = str(candidate.get("kind") or "").strip().lower()
    content = str(candidate.get("content") or "").strip()
    if kind not in {"semantic", "episodic", "procedural"} or not content:
        return None
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    memory_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        stored_id = session.execute(
            text(
                """
                INSERT INTO secretariat.memory_units(
                  id, tenant_id, owner_user_id, conversation_id,
                  kind, scope, content, content_sha256,
                  confidence, salience, evidence, metadata
                ) VALUES (
                  :id, :tenant_id, :owner_user_id,
                  (SELECT conversation_id FROM secretariat.runs
                   WHERE id = :run_id LIMIT 1),
                  :kind, 'private', :content, :content_sha256,
                  :confidence, :salience, CAST(:evidence AS jsonb),
                  CAST(:metadata AS jsonb)
                )
                ON CONFLICT DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": memory_id,
                "tenant_id": actor.tenant_id,
                "owner_user_id": actor.user_id,
                "run_id": run_id,
                "kind": kind,
                "content": content,
                "content_sha256": digest,
                "confidence": max(
                    0.0,
                    min(float(_number(candidate.get("confidence"), 0.5)), 1.0),
                ),
                "salience": max(
                    0.0,
                    min(float(_number(candidate.get("salience"), 0.5)), 1.0),
                ),
                "evidence": json.dumps([{"type": "runtime_run", "id": str(run_id)}]),
                "metadata": json.dumps(
                    {
                        "distilled_by": "auto_runtime_reflection",
                        "run_id": str(run_id),
                        "reason": candidate.get("reason"),
                        "memory_is_not_authority": True,
                    },
                    ensure_ascii=False,
                ),
            },
        ).scalar_one_or_none()
        if stored_id is None:
            stored_id = session.execute(
                text(
                    """
                    SELECT id
                    FROM secretariat.memory_units
                    WHERE owner_user_id = :owner_user_id
                      AND scope = 'private'
                      AND kind = :kind
                      AND content_sha256 = :content_sha256
                    LIMIT 1
                    """
                ),
                {
                    "owner_user_id": actor.user_id,
                    "kind": kind,
                    "content_sha256": digest,
                },
            ).scalar_one()
    return str(stored_id)


def _route_goal(
    connection: object,
    goal: str,
    layers: dict[str, object],
    metrics: list[dict[str, object]],
    *,
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> tuple[dict[str, object], str]:
    """Route from a compact world map without loading exact tools or live data."""
    l0 = layers.get("L0_permanent_world_map")
    l0 = l0 if isinstance(l0, dict) else {}
    l1 = layers.get("L1_current_company_and_people")
    l1 = l1 if isinstance(l1, dict) else {}
    l2 = layers.get("L2_current_goal")
    l2 = l2 if isinstance(l2, dict) else {}
    l3 = layers.get("L3_execution_working_set")
    l3 = l3 if isinstance(l3, dict) else {}
    atlas = [
        [
            item.get("domain"),
            item.get("label"),
            item.get("scope"),
            item.get("gene_count"),
            item.get("active_count"),
            item.get("command_families") or [],
        ]
        for item in l0.get("capability_atlas") or []
        if isinstance(item, dict)
    ]
    router_world = {
        "company": l1.get("company_summary") or {},
        "interaction": l1.get("current_interaction") or {},
        "capability_atlas_columns": [
            "domain",
            "label",
            "scope",
            "gene_count",
            "active_count",
            "command_families",
        ],
        "capability_atlas": atlas,
        "catalogue_candidates": ai_capability_candidates(goal, limit=8),
        "capability_gene_count": l0.get("capability_gene_count"),
        "resource_atlas": [
            {
                "resource_key": item.get("resource_key"),
                "label": item.get("label"),
                "description": item.get("description"),
                "allowed_effects": item.get("allowed_effects") or [],
                "direct_field_count": item.get("direct_field_count"),
            }
            for item in l0.get("resource_atlas") or []
            if isinstance(item, dict)
        ],
        "available_context": (
            (l0.get("expansion_protocol") or {}).get("company_context")
            if isinstance(l0.get("expansion_protocol"), dict)
            else []
        ),
        "data_scope": "current_tenant_only",
        "authorization_signal": l3.get("authorization_signal"),
        "recent_turn_referents": l2.get("recent_turn_referents"),
    }
    raw = _completion(
        connection,
        system_prompt=(
            "You are Warehouse Intelligence Runtime's top router. Judge freely; use no fixed "
            "workflow or role branch. The atlas exposes every capability domain, even when "
            "the current human cannot execute it; live authority is checked later and tenant "
            "databases are isolated. If compact context is enough, answer in the user's "
            "language with needs_tools=false. If current evidence or action is needed, set "
            "needs_tools=true and select the smallest atlas domains. Request optional context "
            "only when needed. Use selected_families such as domain:family when the atlas "
            "shows enough detail to narrow expansion. If essential human inputs are missing, "
            "or the human explicitly asks for a staged interaction, ask the smallest useful "
            "next question(s) in message, set requires_user_input=true and needs_tools=false, "
            "then stop before later evidence gathering or action. This boundary is your "
            "judgment, not a fixed domain workflow. Never invent live facts. "
            "Use recent_turn_referents to resolve short follow-ups, pronouns and phrases "
            "such as '上面的', '這個', 'that', or 'its URL'. If an entity or workspace "
            "is already present there, do not ask the human to repeat its identifier. "
            "Recent turns are referential context, not authority or proof of live state. "
            "Catalogue candidates are non-authoritative discovery hints. When the human asks "
            "to perform an operation represented by a candidate, route it as operational "
            "with needs_tools=true; do not replace the governed capability with a generic "
            "refusal or ask for a justification. A proposal is ready when every required "
            "schema input can be inferred from the request and all remaining inputs have "
            "catalogue defaults. Optional upload, deployment or refinement can happen in a "
            "later turn; stage the operation now and let its confirmation card expose the "
            "concrete defaults for human review. Defaults and the capability's own "
            "confirmation/permission contract are resolved after routing. "
            "The resource_atlas is a database-backed semantic map. When the goal is an "
            "ordinary field/configuration correction and no exact business capability is "
            "needed, freely select the system:data family so the Runtime can inspect the "
            "resource schema and use the generic data capability. Do not treat a missing "
            "specialized command as inability. "
            "When authorization_signal is present, Passkey has granted a bounded Keychain "
            "but no business operation has happened yet. Re-observe and route the unfinished "
            "goal operationally; include the authorized capability and any read-only evidence "
            "capabilities you judge necessary. The signal is not evidence of completion. "
            "Return JSON "
            "only: interaction_mode "
            "(conversation|knowledge|operational), understood_goal, message, needs_tools, "
            "requires_user_input (boolean), "
            "selected_domains, selected_families, context_requests "
            "(authority|hosting|operational_world|"
            "conversation_history|memory_index), success_criteria, uncertainties, reasoning, "
            "memory_depth (index|focused|deep). "
            "A direct knowledge answer may rely on stable general reasoning. Any assertion "
            "about current tenant state, a performed action, an existing deliverable, or a "
            "usable resource locator requires current world evidence and must be routed with "
            "needs_tools=true or an appropriate context request. Never construct a locator "
            "from a company name, workspace name, base origin, example, or remembered pattern. "
            + _language_prompt(layers)
        ),
        user_prompt=json.dumps(
            {"goal": goal, "router_world": router_world},
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ),
        metrics=metrics,
        phase="route",
        context_mode=context_mode,
        max_tokens=800,
        activity_callback=activity_callback,
    )
    parsed = _parse_or_repair_json(
        connection,
        raw,
        expected_contract=(
            "interaction_mode, understood_goal, message, needs_tools, "
            "requires_user_input, selected_domains, selected_families, "
            "context_requests, success_criteria, uncertainties, reasoning, memory_depth"
        ),
        metrics=metrics,
        phase="route",
        context_mode=context_mode,
        activity_callback=activity_callback,
        max_tokens=800,
    )
    if parsed is None:
        parsed = {
            "interaction_mode": "conversation",
            "understood_goal": goal,
            "message": localized_structure_failure(_layer_locale(layers)),
            "needs_tools": False,
            "requires_user_input": True,
            "selected_domains": [],
            "selected_families": [],
            "context_requests": [],
            "success_criteria": [],
            "uncertainties": ["The routing response was not structured JSON"],
            "reasoning": "Stopped safely after structured routing repair failed",
            "memory_depth": "index",
        }

    atlas_domains = {
        str(item.get("domain"))
        for item in ai_capability_atlas()
        if item.get("domain")
    }
    selected_domains = [
        str(name)
        for name in parsed.get("selected_domains") or []
        if str(name) in atlas_domains
    ]
    allowed_context = {
        "authority",
        "hosting",
        "operational_world",
        "conversation_history",
        "memory_index",
    }
    context_requests = [
        str(name)
        for name in parsed.get("context_requests") or []
        if str(name) in allowed_context
    ]
    # Compatibility with the original one-pass distiller and its saved/mock
    # responses. Exact tool names still undergo catalogue validation.
    known_genes = ai_capability_gene_index()
    known_by_name = {str(item["tool_name"]): item for item in known_genes}
    known_family_keys = {
        f"{item.get('domain')}:{str(item.get('command') or '').split(maxsplit=1)[0]}"
        for item in known_genes
    }
    selected_families = [
        str(name)
        for name in parsed.get("selected_families") or []
        if str(name) in known_family_keys
    ]
    selected_domains.extend(
        family.split(":", 1)[0] for family in selected_families
    )
    selected_tools = [
        str(name)
        for name in parsed.get("selected_tool_names") or []
        if str(name) in known_by_name
    ]
    if selected_tools and not selected_domains:
        selected_domains = [
            str(known_by_name[name]["domain"]) for name in selected_tools
        ]
    if selected_tools and not selected_families:
        selected_families = [
            (
                f"{known_by_name[name]['domain']}:"
                f"{str(known_by_name[name].get('command') or '').split(maxsplit=1)[0]}"
            )
            for name in selected_tools
        ]
    parsed["selected_tool_names"] = list(dict.fromkeys(selected_tools))[:24]
    parsed["selected_domains"] = list(dict.fromkeys(selected_domains))[:8]
    parsed["selected_families"] = list(dict.fromkeys(selected_families))[:16]
    parsed["context_requests"] = list(dict.fromkeys(context_requests))
    if selected_tools:
        parsed["needs_tools"] = True
        parsed["interaction_mode"] = "operational"
    else:
        parsed["needs_tools"] = bool(parsed.get("needs_tools"))
    parsed["requires_user_input"] = bool(parsed.get("requires_user_input"))
    if parsed["requires_user_input"]:
        # The router, rather than a hard-coded business rule, has decided that
        # the next valid boundary is human input. Do not pay for catalogue,
        # context or planning calls that cannot yet advance the goal.
        parsed["needs_tools"] = False
        parsed["selected_tool_names"] = []
        parsed["context_requests"] = []
    mode = str(parsed.get("interaction_mode") or "").strip().lower()
    parsed["interaction_mode"] = (
        mode if mode in {"conversation", "knowledge", "operational"} else "operational"
    )
    if parsed["interaction_mode"] == "operational" and not parsed["requires_user_input"]:
        # ``operational`` is a model-selected cognitive mode.  Enforce its
        # generic state-machine meaning without interpreting the business goal.
        parsed["needs_tools"] = True
    memory_depth = str(parsed.get("memory_depth") or "index").strip().lower()
    parsed["memory_depth"] = (
        memory_depth if memory_depth in {"index", "focused", "deep"} else "index"
    )
    parsed["message"] = _public_message(
        parsed.get("message"),
        locale=_layer_locale(layers),
    )
    return parsed, raw


def _select_tools(
    connection: object,
    goal: str,
    route: dict[str, object],
    domain_index: list[dict[str, object]],
    metrics: list[dict[str, object]],
    *,
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> tuple[dict[str, object], str]:
    """Select exact genes from the bounded set exposed by domain routing."""
    raw = _completion(
        connection,
        system_prompt=(
            "You are the capability distillation mind of Warehouse Intelligence Runtime. "
            "The top router has already selected relevant domains. Subjectively select only "
            "the exact capability genes whose full schemas and authority relationships must "
            "be expanded. The index is descriptive and has no hidden permission filtering. "
            "Do not infer a fixed workflow. Return JSON only with keys: selected_tool_names "
            "(array using exact tool_name values), context_focus (array), reasoning (string), "
            "memory_depth (index, focused, or deep)."
        ),
        user_prompt=json.dumps(
            {
                "goal": goal,
                "route": route,
                "domain_capability_index": _domain_index_prompt(
                    domain_index,
                    description_chars=150,
                ),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ),
        metrics=metrics,
        phase="select_tools",
        context_mode=context_mode,
        max_tokens=600,
        activity_callback=activity_callback,
    )
    parsed = _parse_or_repair_json(
        connection,
        raw,
        expected_contract=(
            "selected_tool_names (array), context_focus (array), reasoning (string), "
            "memory_depth"
        ),
        metrics=metrics,
        phase="select_tools",
        context_mode=context_mode,
        activity_callback=activity_callback,
        max_tokens=600,
    ) or {
        "selected_tool_names": [],
        "context_focus": [],
        "reasoning": "Structured capability selection was unavailable",
        "memory_depth": route.get("memory_depth") or "index",
    }
    allowed = {
        str(item.get("tool_name"))
        for item in domain_index
        if isinstance(item, dict) and item.get("tool_name")
    }
    parsed["selected_tool_names"] = list(
        dict.fromkeys(
            str(name)
            for name in parsed.get("selected_tool_names") or []
            if str(name) in allowed
        )
    )[:24]
    _emit_activity(
        activity_callback,
        activity_id="model:select_tools",
        kind="model",
        phase="select_tools",
        status="succeeded",
        selected_tool_names=list(parsed["selected_tool_names"]),
    )
    depth = str(parsed.get("memory_depth") or "index").strip().lower()
    parsed["memory_depth"] = depth if depth in {"index", "focused", "deep"} else "index"
    return parsed, raw


def _plan_goal(
    connection: object,
    goal: str,
    layers: dict[str, object],
    responsibility: dict[str, object],
    metrics: list[dict[str, object]],
    *,
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> tuple[dict[str, object], str]:
    l1 = layers.get("L1_current_company_and_people")
    l1 = l1 if isinstance(l1, dict) else {}
    l2 = layers.get("L2_current_goal")
    l2 = l2 if isinstance(l2, dict) else {}
    l3 = layers.get("L3_execution_working_set")
    l3 = l3 if isinstance(l3, dict) else {}
    contextual_evidence = {
        key: l3[key]
        for key in (
            "company_world_observation",
            "conversation_history",
            "memory_capsule",
            "exact_entities",
            "current_errors",
            "authorization_signal",
        )
        if key in l3 and l3[key] not in (None, [], {})
    }
    hosting = l1.get("hosted_application_world")
    if isinstance(hosting, dict) and hosting.get("loaded") is not False:
        contextual_evidence["hosted_application_world"] = hosting
    focused_layers = {
        "company_summary": l1.get("company_summary") or {},
        "goal": l2,
        "selected_capability_genes": l3.get("selected_capability_genes") or [],
        "contextual_evidence": _compact_for_model(contextual_evidence),
        "data_scope": "current_tenant_only",
    }
    raw = _completion(
        connection,
        system_prompt=(
            "You are the autonomous planning and judgment mind of Warehouse Intelligence "
            "Runtime. The goal, compact company world, responsibility projection and "
            "model-selected capability genes are observations, not hard-coded authorization "
            "branches. "
            "Subjectively decide how to proceed, whether each ability should be executed, "
            "whether another person should participate, whether more context is needed, and "
            "what would count as completion. Company boundaries are physical: never request "
            "another tenant's data. Return JSON only with keys: message (string), plan "
            "(array of strings), decisions (array of objects with tool_name, judgment, "
            "arguments, reasoning, continue_after_result), completion_assessment (object). "
            "Use judgment='execute' only when you actually want the Runtime to invoke the "
            "selected gene now. If authorization_signal is present and you judge its "
            "already-reviewed effect should run, select the matching tool and include "
            "authorization_action_id from that signal at the decision object's top level, "
            "never inside arguments. The Runtime then "
            "consumes the exact encrypted arguments server-side; never reconstruct redacted "
            "values. A Keychain is consent evidence, not completion evidence. "
            "The completion assessment is provisional until the independent reflection phase "
            "has linked material world claims to observed evidence. Do not put an unobserved "
            "resource locator or deliverable in message. "
            + _language_prompt(layers)
        ),
        user_prompt=(
            "GOAL="
            + goal
            + "\nLAYERED_WORLD="
            + json.dumps(
                focused_layers,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            )
            + "\nRESPONSIBILITY_FOR_SELECTED_GENES="
            + json.dumps(responsibility, ensure_ascii=False, separators=(",", ":"))
        ),
        metrics=metrics,
        phase="plan",
        context_mode=context_mode,
        max_tokens=1_200,
        activity_callback=activity_callback,
    )
    parsed = _parse_or_repair_json(
        connection,
        raw,
        expected_contract=(
            "message (user-facing prose), plan (array of user-facing steps), decisions "
            "(array of tool_name, judgment, arguments, reasoning, continue_after_result), "
            "completion_assessment"
        ),
        metrics=metrics,
        phase="plan",
        context_mode=context_mode,
        activity_callback=activity_callback,
        max_tokens=1_200,
    ) or {
        "message": localized_structure_failure(_layer_locale(layers)),
        "plan": [
            "observe the distilled company world",
            "resolve relevant capability genes",
            "decide the next action from current evidence",
            "reflect before claiming completion",
        ],
        "decisions": [],
        "completion_assessment": {"complete": False, "reason": "Unstructured plan"},
    }
    parsed["message"] = _public_message(
        parsed.get("message"),
        locale=_layer_locale(layers),
    )
    return parsed, raw


def _reflect(
    connection: object,
    goal: str,
    plan: dict[str, object],
    tool_results: list[dict[str, object]],
    *,
    round_number: int,
    layers: dict[str, object],
    metrics: list[dict[str, object]],
    prior_reflection: dict[str, object] | None = None,
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> dict[str, object]:
    l0 = layers.get("L0_permanent_world_map")
    l0 = l0 if isinstance(l0, dict) else {}
    l3 = layers.get("L3_execution_working_set")
    l3 = l3 if isinstance(l3, dict) else {}
    selected_contract_names: list[str] = []
    for gene in l3.get("selected_capability_genes") or []:
        if not isinstance(gene, dict):
            continue
        schema = gene.get("schema")
        schema = schema if isinstance(schema, dict) else {}
        function = schema.get("function")
        function = function if isinstance(function, dict) else {}
        if function.get("name"):
            selected_contract_names.append(str(function["name"]))
    raw = _completion(
        connection,
        system_prompt=(
            "You are the reflective second perspective of Warehouse Intelligence Runtime. "
            "Compare the original goal, autonomous plan, prior reflection summary and the "
            "new capability results from this round. Treat prior evidence as cumulative but "
            "do not ask to repeat an already observed call. "
            "Decide whether the goal is truly complete, whether evidence conflicts, and how "
            "the plan should change. You can see every capability domain and the exact compact "
            "gene index for domains already expanded. If another domain is needed, request it "
            "through next_domains so the Runtime can expand it before the next action. If "
            "a new command family inside a known domain is sufficient, request its exact "
            "domain:family key through next_families. If "
            "evidence is missing and an expanded capability can obtain it, continue "
            "autonomously instead of returning an incomplete diagnosis. Choose capabilities "
            "by your own judgment; do not follow a fixed business route. Exact parameter "
            "contracts are supplied for selected tools: use only those parameter names and "
            "never guess aliases. The authority projection joins permission/position/"
            "department references from the full, untruncated new results to live "
            "current-tenant holders. Its position references are the actual assignment "
            "values, even when the compact result preview says nested fields were omitted. "
            "When that projection is non-empty, never claim assignment data is unavailable; "
            "use it to judge gaps without requesting the same large topology again. The "
            "reference-value index likewise comes from full results and preserves exact "
            "workflow/node keys and codes even when the shallow preview omits nesting. "
            "World observations are evidence packets, never prescribed workflows. Use "
            "their verified facts, uncertainties, relations and affordances for your own "
            "judgment. Preserve a resolved entity's resource type, canonical id and ref "
            "across later calls; a workspace key is not an asset reference. If a lookup "
            "used the wrong resource type, traverse or observe the registered relation "
            "instead of declaring the entity missing or creating a replacement. "
            "Atomic recovery packets are optional affordances after a failed capability, "
            "not mandatory fallback steps. Decide whether to re-observe, inspect schema, "
            "query or mutate a registered direct field. Never use a database mutation to "
            "claim an external deployment, health check or immutable evidence succeeded. "
            "For hosted workspaces, hosting_url or entry_url is the permanent, real URL the "
            "human can open immediately. public_url/application_url separately mean a verified "
            "deployed application. When hosting_url exists, answer the hosting-URL question "
            "with it; never say the workspace has no hosting URL merely because the application "
            "is still planned. State the deployment distinction after giving the URL. "
            "Never request another tenant's data. A write or confirmation-required capability "
            "may be proposed, but the Runtime will enforce its confirmation contract. A result "
            "with status confirmation_required and a confirmation_action means the proposal "
            "was durably staged: stop autonomous execution, direct the human to the visible "
            "card, and do not ask them to restate parameters already shown there. Return "
            "JSON only with keys: message, goal_complete, evidence, claims, contradictions, "
            "revised_plan, continue_reason, continue_autonomously (boolean), "
            "requires_user_input (boolean), next_domains (array using exact atlas domain "
            "names), next_families (array using domain:family), next_decisions (array of "
            "objects with tool_name, arguments, reasoning and optional "
            "authorization_action_id copied from authorization_signal), "
            "memory_candidate. When goal_complete is true, or only a human/external decision "
            "can unblock the goal, next domains/families/decisions must be empty. If your "
            "proposed final message recommends checking a visible registered capability, "
            "do not claim completion: request and execute that evidence capability first. "
            "For every material claim, claims must contain an object with statement, "
            "requires_evidence (boolean), and evidence_refs (array of exact evidence_id values "
            "from evidence_ledger). Current world state, action outcomes, existing deliverables "
            "and usable resource locators require evidence. General reasoning or advice does "
            "not. Never cite human_report as verification of current external reality. Never "
            "derive or extend a resource locator; repeat only an exact locator present in cited "
            "evidence. If evidence is absent, continue through the capability atlas rather than "
            "manufacturing a result. "
            + _language_prompt(layers)
        ),
        user_prompt=json.dumps(
            {
                "goal": goal,
                "round_number": round_number,
                "plan": plan,
                "prior_reflection": (
                    _compact_for_model(prior_reflection)
                    if prior_reflection
                    else None
                ),
                "authority_projection_for_new_evidence": (
                    _authority_evidence_projection(layers, tool_results)
                ),
                "reference_values_from_full_results": (
                    _reference_value_projection(tool_results)
                ),
                "world_observations_from_full_results": (
                    _world_observation_projection(tool_results)
                ),
                "atomic_recovery_from_full_results": (
                    _atomic_recovery_projection(tool_results)
                ),
                "new_tool_results": _compact_for_model(
                    tool_results,
                    max_depth=4,
                    max_items=8,
                    max_keys=30,
                    max_string=600,
                ),
                "evidence_ledger": _evidence_ledger(
                    goal,
                    layers,
                    list(l3.get("tool_results") or tool_results),
                ),
                "capability_atlas": l0.get("capability_atlas") or [],
                "expanded_domains": l3.get("expanded_domains") or [],
                "expanded_families": l3.get("expanded_families") or [],
                "expanded_domain_capability_index": _domain_index_prompt(
                    list(l3.get("domain_capability_index") or []),
                    description_chars=110,
                ),
                "selected_exact_parameter_contracts": _parameter_contracts(
                    selected_contract_names
                ),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ),
        metrics=metrics,
        phase=f"reflect_{round_number}",
        context_mode=context_mode,
        max_tokens=1_300,
        activity_callback=activity_callback,
    )
    parsed = _parse_or_repair_json(
        connection,
        raw,
        expected_contract=(
            "message, goal_complete, evidence, claims, contradictions, revised_plan, "
            "continue_reason, continue_autonomously, requires_user_input, next_domains, "
            "next_families, next_decisions, memory_candidate"
        ),
        metrics=metrics,
        phase=f"reflect_{round_number}",
        context_mode=context_mode,
        activity_callback=activity_callback,
        max_tokens=1_300,
    ) or {
        "message": localized_structure_failure(_layer_locale(layers)),
        "goal_complete": False,
        "evidence": [],
        "contradictions": ["Reflection response was not structured JSON"],
        "revised_plan": plan.get("plan") or [],
        "continue_reason": "Structured reflection unavailable",
        "continue_autonomously": False,
        "requires_user_input": True,
        "next_domains": [],
        "next_families": [],
        "next_decisions": [],
        "memory_candidate": None,
    }
    parsed["message"] = _public_message(
        parsed.get("message"),
        locale=_layer_locale(layers),
    )
    return parsed


def _decision_signature(tool_name: str, arguments: dict[str, object]) -> str:
    return json.dumps(
        {"tool_name": tool_name, "arguments": arguments},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _apply_declarative_tool_composition(
    decisions: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Suppress lower-level steps already provided by a selected composite.

    The relation lives in catalogue metadata. This keeps the Runtime generic:
    adding another composite operation never requires a domain-specific branch
    in the planner or executor.
    """

    executing = {
        str(item.get("tool_name") or "")
        for item in decisions
        if str(item.get("judgment") or "").strip().lower() == "execute"
    }
    superseded_by: dict[str, str] = {}
    for item in decisions:
        source = str(item.get("tool_name") or "")
        if source not in executing:
            continue
        entry = entry_by_tool_name(source)
        for target in (entry or {}).get("supersedes_tools") or []:
            normalized = str(target or "").strip()
            if normalized in executing and normalized != source:
                superseded_by.setdefault(normalized, source)
    return [
        (
            {
                **item,
                "judgment": "superseded",
                "reasoning": (
                    f"Provided by composite capability {superseded_by[tool_name]}"
                ),
                "superseded_by": superseded_by[tool_name],
            }
            if tool_name in superseded_by
            and str(item.get("judgment") or "").strip().lower() == "execute"
            else item
        )
        for item in decisions
        for tool_name in [str(item.get("tool_name") or "")]
    ]


def _normalise_continuation_decisions(
    reflection: dict[str, object],
    *,
    known_tool_names: set[str],
) -> list[dict[str, object]]:
    decisions: list[dict[str, object]] = []
    for item in reflection.get("next_decisions") or []:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or "").strip()
        if tool_name not in known_tool_names:
            continue
        arguments = item.get("arguments")
        decisions.append(
            {
                **item,
                "tool_name": tool_name,
                "judgment": "execute",
                "arguments": arguments if isinstance(arguments, dict) else {},
                "continue_after_result": True,
            }
        )
    return _apply_declarative_tool_composition(decisions)[:_MAX_CONTINUATION_DECISIONS]


def _answer_with_expanded_context(
    connection: object,
    goal: str,
    route: dict[str, object],
    layers: dict[str, object],
    metrics: list[dict[str, object]],
    *,
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> tuple[dict[str, object], str]:
    raw = _completion(
        connection,
        system_prompt=(
            "You are Warehouse Intelligence Runtime completing a non-operational answer "
            "after the router requested narrowly scoped context. Answer in the user's "
            "language from the supplied current-tenant evidence. Do not invent facts and do "
            "not treat memory as authority. Return JSON only with keys: message, "
            "goal_complete, evidence, uncertainties, revised_plan, memory_candidate. "
            + _language_prompt(layers)
        ),
        user_prompt=json.dumps(
            {"goal": goal, "route": route, "expanded_context": layers},
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ),
        metrics=metrics,
        phase="answer_with_context",
        context_mode=context_mode,
        max_tokens=1_200,
        activity_callback=activity_callback,
    )
    parsed = _parse_or_repair_json(
        connection,
        raw,
        expected_contract=(
            "message, goal_complete, evidence, uncertainties, revised_plan, memory_candidate"
        ),
        metrics=metrics,
        phase="answer_with_context",
        context_mode=context_mode,
        activity_callback=activity_callback,
        max_tokens=1_200,
    ) or {
        "message": localized_structure_failure(_layer_locale(layers)),
        "goal_complete": False,
        "evidence": [],
        "uncertainties": ["Structured answer unavailable"],
        "revised_plan": ["understand the request", "answer from expanded context"],
        "memory_candidate": None,
    }
    parsed["message"] = _public_message(
        parsed.get("message"),
        locale=_layer_locale(layers),
    )
    return parsed, raw


def _continuation_decisions(
    connection: object,
    goal: str,
    reflection: dict[str, object],
    layers: dict[str, object],
    metrics: list[dict[str, object]],
    *,
    round_number: int,
    executed_signatures: set[str],
    context_mode: str,
    activity_callback: RuntimeActivityCallback | None,
) -> list[dict[str, object]]:
    l3 = layers.get("L3_execution_working_set")
    l3 = l3 if isinstance(l3, dict) else {}
    known = {
        str(item.get("tool_name"))
        for item in l3.get("domain_capability_index") or []
        if isinstance(item, dict) and item.get("tool_name")
    }
    raw = _completion(
        connection,
        system_prompt=(
            "You are Warehouse Intelligence Runtime choosing the next exact evidence calls "
            "after reflection expanded additional capability domains. Decide autonomously "
            "from the bounded gene index. Previously executed tool/argument pairs are supplied; "
            "do not repeat them. Prefer an unexecuted exact-detail capability that resolves "
            "the stated evidence gap. Exact parameter contracts are supplied: use only their "
            "declared parameter names and never guess aliases. Return JSON only with key "
            "next_decisions, an array of "
            "objects containing exact tool_name, arguments and reasoning. Do not propose a "
            "tool outside this index."
        ),
        user_prompt=json.dumps(
            {
                "goal": goal,
                "round_number": round_number,
                "reflection": reflection,
                "previously_executed": [
                    json.loads(signature) for signature in sorted(executed_signatures)
                ],
                "domain_capability_index": _domain_index_prompt(
                    list(l3.get("domain_capability_index") or []),
                    description_chars=140,
                ),
                "exact_parameter_contracts": _parameter_contracts(sorted(known)),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ),
        metrics=metrics,
        phase=f"continue_select_{round_number}",
        context_mode=context_mode,
        max_tokens=700,
        activity_callback=activity_callback,
    )
    parsed = _parse_or_repair_json(
        connection,
        raw,
        expected_contract="next_decisions (array of tool_name, arguments, reasoning)",
        metrics=metrics,
        phase=f"continue_select_{round_number}",
        context_mode=context_mode,
        activity_callback=activity_callback,
        max_tokens=700,
    ) or {"next_decisions": []}
    return [
        decision
        for decision in _normalise_continuation_decisions(
            parsed,
            known_tool_names=known,
        )
        if _decision_signature(
            str(decision["tool_name"]),
            (
                decision["arguments"]
                if isinstance(decision.get("arguments"), dict)
                else {}
            ),
        )
        not in executed_signatures
    ]


def _authority_counts(layers: dict[str, object]) -> dict[str, int]:
    l1 = layers.get("L1_current_company_and_people")
    l1 = l1 if isinstance(l1, dict) else {}
    authority = l1.get("company_authority_world")
    if isinstance(authority, dict) and isinstance(authority.get("departments"), list):
        return {
            "departments": len(authority.get("departments") or []),
            "positions": len(authority.get("positions") or []),
            "people": len(authority.get("people") or []),
        }
    summary = l1.get("company_summary")
    summary = summary if isinstance(summary, dict) else {}
    counts = summary.get("authority_counts")
    counts = counts if isinstance(counts, dict) else {}
    return {
        "departments": int(counts.get("departments") or 0),
        "positions": int(counts.get("positions") or 0),
        "people": int(counts.get("people") or 0),
    }


def _public_observations(
    actor: ActorContext,
    *,
    surface: str,
    conversation_id: str | None,
    layers: dict[str, object],
    selected_history: list[str],
    metrics: list[dict[str, object]],
) -> dict[str, object]:
    l3 = layers.get("L3_execution_working_set")
    l3 = l3 if isinstance(l3, dict) else {}
    return {
        "world": "warehouse_os",
        "scope": "current_tenant_only",
        "company": {"slug": actor.tenant_slug, "name": actor.tenant_name},
        "surface": surface,
        "conversation_id": conversation_id,
        "context_architecture": "hierarchical_funnel_v2",
        "context_strategy": "domain_then_family_then_exact_tool_then_live_data",
        "capability_domains": len(ai_capability_atlas()),
        "capability_genes": sum(
            int(item.get("gene_count") or 0) for item in ai_capability_atlas()
        ),
        "semantic_resources": int(
            (layers.get("L0_permanent_world_map") or {}).get("resource_count") or 0
        ),
        "expanded_domains": list(l3.get("expanded_domains") or []),
        "expanded_families": list(l3.get("expanded_families") or []),
        "selected_capability_genes": selected_history,
        "authority_world": _authority_counts(layers),
        "database": l3.get("company_world_observation") or {},
        "context_metrics": _context_metrics(metrics),
    }


def run_auto_runtime(
    actor: ActorContext,
    settings: Settings,
    goal: str,
    *,
    surface: str = "assistant",
    conversation_id: str | None = None,
    run_id: str | None = None,
    context_mode: str = "balanced",
    response_locale: str | None = None,
    activity_callback: RuntimeActivityCallback | None = None,
    authorization_signal: dict[str, object] | None = None,
) -> RuntimeResult:
    """Run one goal through a lazy domain → tool → data context funnel."""
    normalized_goal = goal.strip()
    if not normalized_goal:
        raise ValueError("A goal is required")
    normalized_context_mode = (
        "thinking" if str(context_mode).strip().lower() == "thinking" else "balanced"
    )
    normalized_response_locale = normalize_locale(response_locale, fallback=None)
    if normalized_response_locale is None:
        normalized_response_locale = resolve_language_contract(normalized_goal).locale
    try:
        runtime_run_id = UUID(str(run_id)) if run_id else uuid4()
    except ValueError:
        runtime_run_id = uuid4()
    company_ai = _company_ai_actor(actor)
    layers = build_router_context(
        company_ai,
        normalized_goal,
        surface=surface,
        conversation_id=conversation_id,
        context_mode=normalized_context_mode,
    )
    # The top router always receives one very small recent-turn capsule. This
    # resolves references such as "上面的" or "its URL" without hydrating the
    # full transcript and memory fabric on every turn.
    if conversation_id:
        try:
            recent_referents = recent_conversation_context(
                actor,
                conversation_id,
                limit=8,
                character_budget=3_000,
            )
        except Exception:
            # Referents are helpful context, never an availability dependency.
            recent_referents = None
        recent_layer = layers.get("L2_current_goal")
        if isinstance(recent_layer, dict) and recent_referents:
            recent_layer["recent_turn_referents"] = recent_referents
    bounded_authorization: dict[str, object] | None = None
    if (
        isinstance(authorization_signal, dict)
        and authorization_signal.get("executable") is True
    ):
        action = authorization_signal.get("action")
        action = action if isinstance(action, dict) else {}
        bounded_authorization = {
            "signal": "authorization_granted",
            "business_operation_executed": False,
            "action_id": authorization_signal.get("action_id"),
            "tool_name": authorization_signal.get("tool_name"),
            "command": authorization_signal.get("command"),
            "presentation": action.get("presentation") or {},
            "expires_at": authorization_signal.get("expires_at"),
            "scope": authorization_signal.get("scope") or {},
            "instruction": (
                "Re-observe current-tenant state. If the approved effect is still needed, "
                "choose this tool with authorization_action_id; exact arguments remain "
                "encrypted and are consumed server-side."
            ),
        }
        authorization_l3 = layers.get("L3_execution_working_set")
        if isinstance(authorization_l3, dict):
            authorization_l3["authorization_signal"] = bounded_authorization
    language_layer = layers.get("L2_current_goal")
    if isinstance(language_layer, dict):
        language_layer["language_contract"] = {
            "locale": normalized_response_locale,
            "instruction": language_instruction(normalized_response_locale),
        }
    phase_metrics: list[dict[str, object]] = []
    _start_run(
        actor,
        run_id=runtime_run_id,
        conversation_id=conversation_id,
        goal=normalized_goal,
        layers=layers,
    )
    try:
        configured_connection = connected_deepseek(actor, settings)
        connection = ModelConnection(
            base_url=configured_connection.base_url,
            model=DEEPSEEK_RUNTIME_MODELS[normalized_context_mode],
            api_key=configured_connection.api_key,
        )
        route, _ = _route_goal(
            connection,
            normalized_goal,
            layers,
            phase_metrics,
            context_mode=normalized_context_mode,
            activity_callback=activity_callback,
        )
        if bounded_authorization is not None:
            authorized_tool = str(bounded_authorization.get("tool_name") or "")
            authorized_gene = entry_by_tool_name(authorized_tool)
            selected_tools = [
                str(item) for item in route.get("selected_tool_names") or []
            ]
            if authorized_tool and authorized_tool not in selected_tools:
                selected_tools.append(authorized_tool)
            route["selected_tool_names"] = selected_tools
            route["needs_tools"] = True
            route["requires_user_input"] = False
            route["interaction_mode"] = "operational"
            if authorized_gene is not None:
                domain = str(authorized_gene.get("domain") or "")
                family = (
                    f"{domain}:"
                    f"{str(authorized_gene.get('command') or '').split(maxsplit=1)[0]}"
                )
                domains = [str(item) for item in route.get("selected_domains") or []]
                families = [str(item) for item in route.get("selected_families") or []]
                if domain and domain not in domains:
                    domains.append(domain)
                if domain and family not in families:
                    families.append(family)
                route["selected_domains"] = domains
                route["selected_families"] = families
        l2 = layers["L2_current_goal"]
        if isinstance(l2, dict):
            l2.update(
                {
                    "understood_goal": route.get("understood_goal"),
                    "success_criteria": route.get("success_criteria") or [],
                    "uncertainties": route.get("uncertainties") or [],
                    "interaction_mode": route.get("interaction_mode"),
                    "selected_domains": route.get("selected_domains") or [],
                }
            )

        l3 = layers["L3_execution_working_set"]
        l3 = l3 if isinstance(l3, dict) else {}

        def hydrate_requested_context(
            requests: list[str],
            *,
            memory_depth: str,
        ) -> None:
            requested = set(requests)
            if "authority" in requested:
                hydrate_company_authority(layers, company_ai)
            if "hosting" in requested:
                hydrate_hosting_world(layers, company_ai)
            if "operational_world" in requested:
                l3["company_world_observation"] = runtime_world_snapshot(company_ai)
            if "conversation_history" in requested and conversation_id:
                hydrate_recent_context(layers, actor, conversation_id)
                l3["conversation_history"] = recent_conversation_context(
                    actor,
                    conversation_id,
                )
            if "memory_index" in requested:
                if conversation_id:
                    l3["memory_capsule"] = build_memory_capsule(
                        actor,
                        conversation_id=conversation_id,
                        query=normalized_goal,
                        depth=memory_depth,
                    )
                    layers["L5_experience_memory"] = {
                        "loaded": True,
                        "depth": memory_depth,
                        "capsule": l3["memory_capsule"],
                    }
                else:
                    hydrate_experience_memory(layers, actor)

        context_requests = [
            str(item) for item in route.get("context_requests") or []
        ]
        requested_memory_depth = str(route.get("memory_depth") or "index")
        hydrate_requested_context(
            context_requests,
            memory_depth=requested_memory_depth,
        )

        # Ordinary conversation can finish at the router boundary. Knowledge
        # answers receive an independent reflective pass; that pass may decide
        # the proposed answer actually needs current evidence and send the goal
        # into the same dynamic capability loop as any other operation.
        if not bool(route.get("needs_tools")):
            if context_requests:
                direct, _ = _answer_with_expanded_context(
                    connection,
                    normalized_goal,
                    route,
                    layers,
                    phase_metrics,
                    context_mode=normalized_context_mode,
                    activity_callback=activity_callback,
                )
            else:
                requires_user_input = bool(route.get("requires_user_input"))
                direct = {
                    "message": route.get("message") or "",
                    "goal_complete": not requires_user_input,
                    "evidence": [],
                    "uncertainties": route.get("uncertainties") or [],
                    "revised_plan": [
                        "understand the request",
                        "respond from compact current-tenant context",
                    ],
                    "memory_candidate": route.get("memory_candidate"),
                }
            direct_review: dict[str, object] | None = None
            if (
                str(route.get("interaction_mode") or "conversation") != "conversation"
                and not bool(route.get("requires_user_input"))
            ):
                direct_plan = {
                    "message": direct.get("message") or route.get("message") or "",
                    "plan": direct.get("revised_plan") or [],
                    "decisions": [],
                    "completion_assessment": {
                        "complete": bool(direct.get("goal_complete", True)),
                        "reason": "proposed non-operational answer",
                    },
                }
                direct_review = _reflect(
                    connection,
                    normalized_goal,
                    direct_plan,
                    [],
                    round_number=0,
                    layers=layers,
                    metrics=phase_metrics,
                    context_mode=normalized_context_mode,
                    activity_callback=activity_callback,
                )
                direct_review = _apply_reflection_evidence_contract(
                    direct_review,
                    interaction_mode=str(route.get("interaction_mode") or "knowledge"),
                    ledger=_evidence_ledger(normalized_goal, layers, []),
                )
                requested_domains = [
                    str(item) for item in direct_review.get("next_domains") or []
                ]
                requested_families = [
                    str(item) for item in direct_review.get("next_families") or []
                ]
                known_genes = {
                    str(item.get("tool_name")): item
                    for item in ai_capability_gene_index()
                    if isinstance(item, dict) and item.get("tool_name")
                }
                requested_tool_names = [
                    str(item.get("tool_name"))
                    for item in direct_review.get("next_decisions") or []
                    if isinstance(item, dict)
                    and str(item.get("tool_name")) in known_genes
                ]
                requested_domains.extend(
                    str(known_genes[name].get("domain") or "")
                    for name in requested_tool_names
                )
                requested_families.extend(
                    (
                        f"{known_genes[name].get('domain')}:"
                        f"{str(known_genes[name].get('command') or '').split(maxsplit=1)[0]}"
                    )
                    for name in requested_tool_names
                )
                if bool(direct_review.get("continue_autonomously")) and any(
                    (requested_domains, requested_families, requested_tool_names)
                ):
                    route["needs_tools"] = True
                    route["interaction_mode"] = "operational"
                    route["selected_domains"] = list(
                        dict.fromkeys(item for item in requested_domains if item)
                    )[:8]
                    route["selected_families"] = list(
                        dict.fromkeys(item for item in requested_families if item)
                    )[:16]
                    route["selected_tool_names"] = list(
                        dict.fromkeys(requested_tool_names)
                    )[:24]
                    route["reasoning"] = direct_review.get("continue_reason")
                    if isinstance(l2, dict):
                        l2["interaction_mode"] = "operational"
                        l2["selected_domains"] = route["selected_domains"]

            if not bool(route.get("needs_tools")):
                if direct_review is not None:
                    direct["message"] = direct_review.get("message") or direct.get("message")
                    direct["goal_complete"] = bool(direct_review.get("goal_complete"))
                    direct["revised_plan"] = direct_review.get("revised_plan") or []
                    direct["memory_candidate"] = direct_review.get("memory_candidate")
                message = str(
                    direct.get("message") or route.get("message") or ""
                ).strip()
                if not message:
                    message = localized_empty_answer(normalized_response_locale)
                message = _ensure_message_locale(
                    connection,
                    message,
                    normalized_response_locale,
                    phase_metrics,
                    context_mode=normalized_context_mode,
                    activity_callback=activity_callback,
                )
                direct_ledger = _evidence_ledger(normalized_goal, layers, [])
                direct_sources = _grounding_source_values(normalized_goal, layers, [])
                review_grounding = (
                    direct_review.get("grounding")
                    if isinstance(direct_review, dict)
                    and isinstance(direct_review.get("grounding"), dict)
                    else {}
                )
                message, grounding_repair = _finalize_grounded_message(
                    connection,
                    goal=normalized_goal,
                    message=message,
                    locale=normalized_response_locale,
                    ledger=direct_ledger,
                    grounding_sources=direct_sources,
                    public_origin=getattr(settings, "public_origin", None),
                    unsupported_claims=[
                        str(item)
                        for item in review_grounding.get("unsupported_claims") or []
                    ],
                    force_reconciliation=bool(
                        review_grounding.get("operational_without_world_evidence")
                    ),
                    metrics=phase_metrics,
                    context_mode=normalized_context_mode,
                    activity_callback=activity_callback,
                )
                grounding_failed = bool(grounding_repair.get("reconciled"))
                reflection = direct_review or {
                    "message": message,
                    "goal_complete": bool(direct.get("goal_complete", True)),
                    "evidence": direct.get("evidence") or [],
                    "claims": [],
                    "contradictions": [],
                    "revised_plan": direct.get("revised_plan") or [],
                    "continue_reason": (
                        "waiting_for_human_input"
                        if bool(route.get("requires_user_input"))
                        else "answered_without_operational_tools"
                    ),
                    "continue_autonomously": False,
                    "requires_user_input": bool(route.get("requires_user_input")),
                    "next_domains": [],
                    "next_families": [],
                    "next_decisions": [],
                    "memory_candidate": direct.get("memory_candidate"),
                }
                reflection["message"] = message
                reflection["goal_complete"] = (
                    bool(reflection.get("goal_complete")) and not grounding_failed
                )
                reflection["runtime_stop_reason"] = (
                    "requires_user_input"
                    if bool(route.get("requires_user_input"))
                    else (
                        "evidence_not_grounded"
                        if grounding_failed
                        else (
                            "goal_complete"
                            if bool(reflection.get("goal_complete"))
                            else "evidence_exhausted"
                        )
                    )
                )
                reflection["autonomous_rounds"] = 0
                reflection["reasoning_rounds"] = []
                review_grounding.update(
                    {
                        "contract": "warehouse.claim-evidence.v1",
                        "evidence_ids": [
                            str(item["evidence_id"])
                            for item in direct_ledger
                            if item.get("evidence_id")
                        ],
                        "message_repair": grounding_repair,
                    }
                )
                reflection["grounding"] = review_grounding
                if grounding_failed:
                    reflection["memory_candidate"] = None
                memory_id = _persist_memory_candidate(
                    actor,
                    run_id=runtime_run_id,
                    candidate=reflection.get("memory_candidate"),
                )
                if memory_id:
                    reflection["memory_id"] = memory_id
                observations = _public_observations(
                    actor,
                    surface=surface,
                    conversation_id=conversation_id,
                    layers=layers,
                    selected_history=[],
                    metrics=phase_metrics,
                )
                final_snapshot = {
                    "architecture": "hierarchical_funnel_v2",
                    "route": route,
                    "distillation": route,
                    "decisions": [],
                    "tool_results": [],
                    "reflection": reflection,
                    "context_metrics": _context_metrics(phase_metrics),
                    "layers": layers,
                }
                _finish_run(
                    actor,
                    run_id=runtime_run_id,
                    status="succeeded",
                    snapshot=final_snapshot,
                )
                return RuntimeResult(
                    goal=normalized_goal,
                    message=message,
                    model=connection.model,
                    observations=observations,
                    plan=_public_plan_steps(
                        reflection["revised_plan"],
                        locale=normalized_response_locale,
                    ),
                    run_id=str(runtime_run_id),
                    distillation=route,
                    decisions=(),
                    tool_results=(),
                    reflection=reflection,
                    response_locale=normalized_response_locale,
                )

        domain_index = expand_capability_domains(
            layers,
            [str(item) for item in route.get("selected_domains") or []],
            family_keys=[
                str(item) for item in route.get("selected_families") or []
            ],
        )
        if route.get("selected_tool_names"):
            selection = {
                "selected_tool_names": route.get("selected_tool_names") or [],
                "context_focus": route.get("context_focus") or [],
                "reasoning": route.get("reasoning"),
                "memory_depth": requested_memory_depth,
            }
        elif domain_index:
            selection, _ = _select_tools(
                connection,
                normalized_goal,
                route,
                domain_index,
                phase_metrics,
                context_mode=normalized_context_mode,
                activity_callback=activity_callback,
            )
        else:
            selection = {
                "selected_tool_names": [],
                "context_focus": [],
                "reasoning": "No capability domain was selected by the router",
                "memory_depth": requested_memory_depth,
            }
        distillation = {
            **route,
            **selection,
            "selected_domains": route.get("selected_domains") or [],
            "success_criteria": route.get("success_criteria") or [],
            "uncertainties": route.get("uncertainties") or [],
        }
        if isinstance(l2, dict):
            l2["context_focus"] = distillation.get("context_focus") or []

        selected_history = [
            str(item) for item in distillation.get("selected_tool_names") or []
        ]
        _emit_activity(
            activity_callback,
            activity_id="capability:selection",
            kind="selection",
            phase="capability_selection",
            status="succeeded",
            selected_tool_names=list(selected_history),
            count=len(selected_history),
        )
        genes = expand_selected_capabilities(layers, selected_history)
        # Once exact operational genes exist, expand the full tenant-local
        # authority graph so AI judgment can connect actions to responsible
        # positions and people, even if the current human lacks permission.
        if genes:
            hydrate_company_authority(layers, company_ai)
        responsibility = responsibility_for_genes(layers, genes)
        if isinstance(l3, dict):
            l3["responsibility_for_selected_genes"] = responsibility

        planned, _ = _plan_goal(
            connection,
            normalized_goal,
            layers,
            responsibility,
            phase_metrics,
            context_mode=normalized_context_mode,
            activity_callback=activity_callback,
        )
        selected_names = {str(name) for name in distillation.get("selected_tool_names") or []}
        decisions = _apply_declarative_tool_composition(
            [
                dict(item)
                for item in planned.get("decisions") or []
                if isinstance(item, dict)
            ]
        )
        capability_metadata = {
            str(item.get("tool_name")): item
            for item in ai_capability_gene_index()
            if isinstance(item, dict) and item.get("tool_name")
        }
        for decision_index, decision in enumerate(decisions):
            judgment = str(decision.get("judgment") or "").strip().lower()
            if judgment == "execute":
                continue
            tool_name = str(decision.get("tool_name") or "").strip()
            if not tool_name:
                continue
            metadata = capability_metadata.get(tool_name) or {}
            _emit_activity(
                activity_callback,
                activity_id=f"decision:1:{decision_index}:{tool_name}",
                kind="capability",
                phase="decision",
                status=(
                    "requires_user_input"
                    if judgment in {"ask_person", "requires_user_input"}
                    else "skipped"
                ),
                tool_name=tool_name,
                command=str(metadata.get("command") or ""),
                description=str(metadata.get("description") or ""),
                judgment=judgment or "skipped",
                round=1,
            )
        all_decisions = [{**item, "runtime_round": 1} for item in decisions]
        tool_results: list[dict[str, object]] = []
        transient_credentials: list[dict[str, object]] = []
        pending_confirmation_actions: list[dict[str, object]] = []
        download_markers: list[dict[str, object]] = []
        download_urls: set[str] = set()
        executed_signatures: set[str] = set()
        secure_delivery_started: dict[str, float] = {}
        rounds: list[dict[str, object]] = []

        def execute_batch(
            batch: list[dict[str, object]],
            *,
            allowed_names: set[str],
            round_number: int,
        ) -> list[str]:
            executed_names: list[str] = []
            for decision in batch:
                if len(tool_results) >= _MAX_AUTONOMOUS_TOOL_CALLS:
                    break
                tool_name = str(decision.get("tool_name") or "")
                if (
                    tool_name not in allowed_names
                    or str(decision.get("judgment") or "").strip().lower() != "execute"
                ):
                    continue
                arguments = decision.get("arguments")
                safe_arguments = arguments if isinstance(arguments, dict) else {}
                signature = _decision_signature(tool_name, safe_arguments)
                if signature in executed_signatures:
                    continue
                executed_signatures.add(signature)
                metadata = capability_metadata.get(tool_name) or {}
                activity_id = (
                    f"tool:{round_number}:{len(tool_results) + 1}:{tool_name}"
                )
                tool_started = perf_counter()
                _emit_activity(
                    activity_callback,
                    activity_id=activity_id,
                    kind="capability",
                    phase="execute",
                    status="running",
                    tool_name=tool_name,
                    command=str(metadata.get("command") or ""),
                    description=str(metadata.get("description") or ""),
                    round=round_number,
                )
                try:
                    authorization_action_id = (
                        decision.get("authorization_action_id")
                        or safe_arguments.get("authorization_action_id")
                    )
                    consumes_authorization = bool(
                        bounded_authorization is not None
                        and tool_name
                        == str(bounded_authorization.get("tool_name") or "")
                        and str(authorization_action_id or "")
                        == str(bounded_authorization.get("action_id") or "")
                    )
                    if consumes_authorization:
                        result = execute_authorized_confirmation_action(
                            actor,
                            bounded_authorization["action_id"],
                            authorization_keychain_id=authorization_signal[
                                "authorization_keychain_id"
                            ],
                            conversation_id=conversation_id,
                            settings=settings,
                        )
                    else:
                        result = execute_runtime_tool_call(
                            (
                                actor
                                if metadata.get("execution_identity")
                                == "requesting_user"
                                else company_ai
                            ),
                            tool_name,
                            safe_arguments,
                            execution_context={
                                "run_id": str(runtime_run_id),
                                "conversation_id": conversation_id,
                            },
                        )
                except Exception:
                    _emit_activity(
                        activity_callback,
                        activity_id=activity_id,
                        kind="capability",
                        phase="execute",
                        status="failed",
                        tool_name=tool_name,
                        command=str(metadata.get("command") or ""),
                        description=str(metadata.get("description") or ""),
                        round=round_number,
                        elapsed_ms=round((perf_counter() - tool_started) * 1000),
                    )
                    raise
                delivered = result.pop("credentials", [])
                delivered_credentials = [
                    dict(item)
                    for item in (delivered if isinstance(delivered, list) else [])
                    if isinstance(item, dict) and item.get("value")
                ]
                transient_credentials.extend(delivered_credentials)
                action = result.get("action")
                action = action if isinstance(action, dict) else {}
                credential_deliveries = action.get("credential_deliveries")
                has_secure_delivery = bool(
                    delivered_credentials
                    or (
                        isinstance(credential_deliveries, list)
                        and credential_deliveries
                    )
                )
                for download in _safe_download_markers(result):
                    url = str(download["url"])
                    if url not in download_urls:
                        download_urls.add(url)
                        download_markers.append(download)
                raw_status = str(result.get("status") or "").strip().lower()
                if raw_status in {
                    "confirmation_required",
                    "pending_confirmation",
                    "requires_confirmation",
                }:
                    action = propose_confirmation_action(
                        actor,
                        tool_name=tool_name,
                        arguments=safe_arguments,
                        settings=settings,
                        conversation_id=conversation_id,
                        run_id=runtime_run_id,
                        source_step_no=len(tool_results) + 1,
                    )
                    result["confirmation_action"] = action
                    pending_confirmation_actions.append(action)
                    activity_status = "waiting_confirmation"
                elif result.get("ok") is False or raw_status in {
                    "failed",
                    "error",
                    "rejected",
                    "target_rejected",
                    "not_implemented",
                }:
                    activity_status = "failed"
                else:
                    activity_status = "succeeded"
                _emit_activity(
                    activity_callback,
                    activity_id=activity_id,
                    kind="capability",
                    phase="execute",
                    status=activity_status,
                    tool_name=tool_name,
                    command=str(metadata.get("command") or ""),
                    description=str(metadata.get("description") or ""),
                    round=round_number,
                    elapsed_ms=round((perf_counter() - tool_started) * 1000),
                    result_status=raw_status or activity_status,
                )
                if activity_status == "succeeded" and has_secure_delivery:
                    delivery_activity_id = (
                        f"credential_delivery:{round_number}:"
                        f"{len(tool_results) + 1}:{tool_name}"
                    )
                    secure_delivery_started[delivery_activity_id] = perf_counter()
                    _emit_activity(
                        activity_callback,
                        activity_id=delivery_activity_id,
                        kind="credential_delivery",
                        phase="secure_credential_delivery",
                        status="running",
                    )
                tool_results.append(
                    {
                        "evidence_id": activity_id,
                        "runtime_round": round_number,
                        "tool_name": tool_name,
                        "decision_reasoning": decision.get("reasoning"),
                        "result": result,
                    }
                )
                if isinstance(l3, dict):
                    l3["world_observations"] = _world_observation_projection(
                        tool_results
                    )
                    l3["atomic_recovery"] = _atomic_recovery_projection(tool_results)
                executed_names.append(tool_name)
            return executed_names

        initial_executed = execute_batch(
            decisions[:12],
            allowed_names=selected_names,
            round_number=1,
        )
        if isinstance(l3, dict):
            l3["tool_results"] = tool_results

        reflection = _reflect(
            connection,
            normalized_goal,
            planned,
            tool_results,
            round_number=1,
            layers=layers,
            metrics=phase_metrics,
            context_mode=normalized_context_mode,
            activity_callback=activity_callback,
        )
        reflection = _apply_reflection_evidence_contract(
            reflection,
            interaction_mode=str(route.get("interaction_mode") or "operational"),
            ledger=_evidence_ledger(normalized_goal, layers, tool_results),
        )
        if pending_confirmation_actions:
            # Confirmation is a generic execution boundary, not a business
            # workflow rule. Keep the staged card as the only valid next step.
            reflection.update(
                {
                    "goal_complete": False,
                    "continue_autonomously": False,
                    "requires_user_input": False,
                    "continue_reason": "awaiting_passkey_confirmation",
                    "next_domains": [],
                    "next_families": [],
                    "next_decisions": [],
                }
            )
        rounds.append(
            {
                "round": 1,
                "selected_tool_names": list(selected_history),
                "executed_tool_names": initial_executed,
                "goal_complete": bool(reflection.get("goal_complete")),
                "continue_autonomously": bool(reflection.get("continue_autonomously")),
                "continue_reason": reflection.get("continue_reason"),
            }
        )

        stop_reason = "goal_complete"
        if not bool(reflection.get("goal_complete")):
            stop_reason = (
                "requires_user_input"
                if bool(reflection.get("requires_user_input"))
                else "evidence_exhausted"
            )
        for round_number in range(2, _MAX_AUTONOMOUS_ROUNDS + 1):
            if bool(reflection.get("goal_complete")):
                stop_reason = "goal_complete"
                break
            if not bool(reflection.get("continue_autonomously")):
                break
            requested_domains = [
                str(item) for item in reflection.get("next_domains") or []
            ]
            requested_families = [
                str(item) for item in reflection.get("next_families") or []
            ]
            family_domains = [
                family.split(":", 1)[0]
                for family in requested_families
                if ":" in family
            ]
            previous_capability_count = len(
                l3.get("domain_capability_index") or []
            )
            if requested_domains or requested_families:
                expand_capability_domains(
                    layers,
                    list(dict.fromkeys([*requested_domains, *family_domains])),
                    family_keys=requested_families,
                )
            known_tool_names = {
                str(item.get("tool_name"))
                for item in l3.get("domain_capability_index") or []
                if isinstance(item, dict) and item.get("tool_name")
            }
            continuation = _normalise_continuation_decisions(
                reflection,
                known_tool_names=known_tool_names,
            )
            if (
                not continuation
                and len(l3.get("domain_capability_index") or [])
                > previous_capability_count
            ):
                continuation = _continuation_decisions(
                    connection,
                    normalized_goal,
                    reflection,
                    layers,
                    phase_metrics,
                    round_number=round_number,
                    executed_signatures=executed_signatures,
                    context_mode=normalized_context_mode,
                    activity_callback=activity_callback,
                )
            continuation = [
                decision
                for decision in continuation
                if _decision_signature(
                    str(decision["tool_name"]),
                    (
                        decision["arguments"]
                        if isinstance(decision.get("arguments"), dict)
                        else {}
                    ),
                )
                not in executed_signatures
            ]
            if not continuation:
                stop_reason = "evidence_exhausted"
                break
            requested_names = [str(item["tool_name"]) for item in continuation]
            for tool_name in requested_names:
                if tool_name not in selected_names:
                    selected_names.add(tool_name)
                    selected_history.append(tool_name)
            expanded_genes = expand_selected_capabilities(
                layers,
                selected_history,
            )
            responsibility = responsibility_for_genes(layers, expanded_genes)
            if isinstance(l3, dict):
                l3["responsibility_for_selected_genes"] = responsibility
            all_decisions.extend({**item, "runtime_round": round_number} for item in continuation)
            executed_names = execute_batch(
                continuation,
                allowed_names=selected_names,
                round_number=round_number,
            )
            if not executed_names:
                stop_reason = "duplicate_evidence_request"
                break
            if isinstance(l3, dict):
                l3["tool_results"] = tool_results
            prior_reflection = reflection
            reflection = _reflect(
                connection,
                normalized_goal,
                planned,
                [
                    item
                    for item in tool_results
                    if int(item.get("runtime_round") or 0) == round_number
                ],
                round_number=round_number,
                layers=layers,
                metrics=phase_metrics,
                prior_reflection=prior_reflection,
                context_mode=normalized_context_mode,
                activity_callback=activity_callback,
            )
            reflection = _apply_reflection_evidence_contract(
                reflection,
                interaction_mode=str(route.get("interaction_mode") or "operational"),
                ledger=_evidence_ledger(normalized_goal, layers, tool_results),
            )
            if pending_confirmation_actions:
                reflection.update(
                    {
                        "goal_complete": False,
                        "continue_autonomously": False,
                        "requires_user_input": False,
                        "continue_reason": "awaiting_passkey_confirmation",
                        "next_domains": [],
                        "next_families": [],
                        "next_decisions": [],
                    }
                )
            rounds.append(
                {
                    "round": round_number,
                    "selected_tool_names": requested_names,
                    "executed_tool_names": executed_names,
                    "goal_complete": bool(reflection.get("goal_complete")),
                    "continue_autonomously": bool(reflection.get("continue_autonomously")),
                    "continue_reason": reflection.get("continue_reason"),
                }
            )
            if len(tool_results) >= _MAX_AUTONOMOUS_TOOL_CALLS:
                stop_reason = "tool_call_limit"
                break
        else:
            if not bool(reflection.get("goal_complete")):
                stop_reason = "round_limit"

        if pending_confirmation_actions:
            stop_reason = "waiting_confirmation"
        elif bool(reflection.get("goal_complete")):
            stop_reason = "goal_complete"
        elif stop_reason == "goal_complete":
            stop_reason = (
                "requires_user_input"
                if bool(reflection.get("requires_user_input"))
                else "evidence_exhausted"
            )
        reflection["runtime_stop_reason"] = stop_reason
        reflection["autonomous_rounds"] = len(rounds)
        reflection["reasoning_rounds"] = rounds
        message = str(reflection.get("message") or planned.get("message") or "").strip()
        if not message:
            message = localized_empty_plan(normalized_response_locale)
        message = _ensure_message_locale(
            connection,
            message,
            normalized_response_locale,
            phase_metrics,
            context_mode=normalized_context_mode,
            activity_callback=activity_callback,
        )
        grounding = reflection.get("grounding")
        grounding = grounding if isinstance(grounding, dict) else {}
        final_ledger = _evidence_ledger(normalized_goal, layers, tool_results)
        message, grounding_repair = _finalize_grounded_message(
            connection,
            goal=normalized_goal,
            message=message,
            locale=normalized_response_locale,
            ledger=final_ledger,
            grounding_sources=_grounding_source_values(
                normalized_goal,
                layers,
                tool_results,
                download_markers,
            ),
            public_origin=getattr(settings, "public_origin", None),
            unsupported_claims=[
                str(item) for item in grounding.get("unsupported_claims") or []
            ],
            force_reconciliation=bool(
                grounding.get("operational_without_world_evidence")
            ),
            metrics=phase_metrics,
            context_mode=normalized_context_mode,
            activity_callback=activity_callback,
        )
        grounding["message_repair"] = grounding_repair
        reflection["grounding"] = grounding
        if grounding_repair.get("reconciled"):
            reflection["goal_complete"] = False
            reflection["runtime_stop_reason"] = "evidence_not_grounded"
            reflection["memory_candidate"] = None
        reflection["message"] = message
        memory_id = _persist_memory_candidate(
            actor,
            run_id=runtime_run_id,
            candidate=reflection.get("memory_candidate"),
        )
        if memory_id:
            reflection["memory_id"] = memory_id
        plan = _public_plan_steps(
            (
                reflection.get("revised_plan")
                or planned.get("plan")
                or [
                    "observe the layered company world",
                    "understand the goal",
                    "compose capability genes",
                    "reflect on evidence",
                ]
            ),
            locale=normalized_response_locale,
        )
        public_observations = _public_observations(
            actor,
            surface=surface,
            conversation_id=conversation_id,
            layers=layers,
            selected_history=selected_history,
            metrics=phase_metrics,
        )
        final_snapshot = {
            "architecture": "hierarchical_funnel_v2",
            "route": route,
            "distillation": distillation,
            "decisions": all_decisions,
            "tool_results": tool_results,
            "reflection": reflection,
            "context_metrics": _context_metrics(phase_metrics),
            "layers": layers,
        }
        _finish_run(
            actor,
            run_id=runtime_run_id,
            status="succeeded",
            snapshot=final_snapshot,
        )
        for activity_id, started_at in secure_delivery_started.items():
            _emit_activity(
                activity_callback,
                activity_id=activity_id,
                kind="credential_delivery",
                phase="secure_credential_delivery",
                status="succeeded",
                elapsed_ms=round((perf_counter() - started_at) * 1000),
            )
        return RuntimeResult(
            goal=normalized_goal,
            message=message,
            model=connection.model,
            observations=public_observations,
            plan=plan,
            run_id=str(runtime_run_id),
            distillation=distillation,
            decisions=tuple(all_decisions),
            tool_results=tuple(tool_results),
            credentials=tuple(transient_credentials),
            downloads=tuple(download_markers),
            confirmation_actions=tuple(pending_confirmation_actions),
            reflection=reflection,
            response_locale=normalized_response_locale,
        )
    except Exception:
        _finish_run(
            actor,
            run_id=runtime_run_id,
            status="failed",
            snapshot={
                "architecture": "hierarchical_funnel_v2",
                "layers": layers,
                "context_metrics": _context_metrics(phase_metrics),
                "failure": "runtime_exception",
            },
        )
        raise
