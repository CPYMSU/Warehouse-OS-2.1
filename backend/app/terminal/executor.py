"""Single execution boundary shared by the human terminal and AI tool calls."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import create_access_token
from app.terminal import legacy_catalog
from app.terminal.adapters import execute_verified_adapter, verified_adapter_ready
from app.terminal.catalog import (
    availability,
    command_catalogue,
    entry_by_tool_name,
    execution_kind,
    is_authorized,
)
from app.terminal.store import command_audit_writer

if TYPE_CHECKING:
    from app.api.deps import ActorContext

_SECRET_PARTS = ("password", "secret", "token", "api_key", "credential", "passkey", "sql")


class CommandAdapterError(RuntimeError):
    """A target API rejected a structurally valid command request."""

    def __init__(self, status_code: int, payload: object) -> None:
        super().__init__(f"target API returned HTTP {status_code}")
        self.status_code = status_code
        self.payload = payload


def _redacted_values(entry: Mapping[str, Any], values: Mapping[str, object]) -> dict[str, object]:
    """Persist command arguments only after applying catalogue and name redaction."""
    redact_all = bool(entry.get("audit_redact"))
    safe: dict[str, object] = {}
    for key, value in values.items():
        if redact_all or any(part in key.lower() for part in _SECRET_PARTS):
            safe[key] = "[redacted]"
        else:
            safe[key] = value
    return safe


def _redacted_response(
    entry: Mapping[str, Any],
    response: Mapping[str, object],
) -> dict[str, object]:
    """Remove one-time credentials before an execution envelope is audited."""
    secret_fields = {
        str(field).strip().lower()
        for field in (entry.get("secret_result_fields") or [])
        if str(field).strip()
    }

    def visit(value: object, *, key: str = "", in_credentials: bool = False) -> object:
        normalized = key.lower()
        if (
            normalized in secret_fields
            or any(part in normalized for part in _SECRET_PARTS)
            or (in_credentials and normalized == "value")
        ):
            return "[redacted]"
        if isinstance(value, Mapping):
            nested_credentials = in_credentials or normalized in {
                "credential",
                "credentials",
            }
            return {
                str(child_key): visit(
                    child_value,
                    key=str(child_key),
                    in_credentials=nested_credentials,
                )
                for child_key, child_value in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [visit(item, in_credentials=in_credentials) for item in value]
        return value

    redacted = visit(response)
    return dict(redacted) if isinstance(redacted, dict) else {}


def _extract_one_time_credentials(
    entry: Mapping[str, Any],
    data: object,
) -> tuple[object, list[dict[str, object]]]:
    """Move declared secret fields into a transient UI-only envelope."""
    if not isinstance(data, Mapping):
        return data, []
    safe_data = dict(data)
    credentials: list[dict[str, object]] = []
    for raw_field in entry.get("secret_result_fields") or []:
        field = str(raw_field).strip()
        value = safe_data.pop(field, None)
        if not isinstance(value, str) or not value:
            continue
        credentials.append(
            {
                "field": field,
                "kind": ("runtime_api_key" if field == "api_key" else field),
                "value": value,
                "label": safe_data.get("label") or "一次性憑證",
                "key_id": safe_data.get("key_id"),
                "key_hint": (safe_data.get("key_hint") or safe_data.get(f"{field}_hint")),
                "tenant_slug": safe_data.get("tenant_slug"),
                "scopes": list(safe_data.get("scopes") or []),
                "expires_at": safe_data.get("expires_at"),
                "note": safe_data.get("note") or "明文只顯示這一次，請立即保存。",
            }
        )
    return safe_data, credentials


def _envelope(
    *,
    ok: bool,
    command: str,
    tool_name: str,
    status: str,
    writes: bool,
    risk: str,
    data: object | None = None,
    error: str | None = None,
    usage: str | None = None,
    hint: str | None = None,
    elapsed_ms: int = 0,
) -> dict[str, object]:
    result: dict[str, object] = {
        "ok": ok,
        "command": command,
        "tool_name": tool_name,
        "status": status,
        "writes": writes,
        "risk": risk,
        "elapsed_ms": elapsed_ms,
    }
    if data is not None:
        result["data"] = data
    if error:
        result["error"] = error
    if usage:
        result["usage"] = usage
    if hint:
        result["hint"] = hint
    return result


def atomic_recovery_contract(
    entry: Mapping[str, Any] | None,
    values: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Describe the universal data-level recovery surface without prescribing a flow.

    A failed domain adapter is evidence about one attempted action, not evidence that
    the user's goal is impossible.  This packet lets Auto Runtime re-observe the
    semantic or physical database world and use the database Runtime when that
    best serves the goal. It deliberately does not auto-select or auto-execute
    a fallback: planning remains the model's responsibility.
    """

    semantic_contract = dict((entry or {}).get("semantic_contract") or {})
    confirmation_binding = semantic_contract.get("confirmation_binding")
    confirmation_binding = confirmation_binding if isinstance(confirmation_binding, Mapping) else {}
    declared_recovery = [
        {
            "tool_name": str(tool_name),
            "effect": "observe_and_resolve_canonical_resource_for_authorization",
        }
        for tool_name in confirmation_binding.get("resolve_capabilities") or []
        if str(tool_name or "").strip()
    ]
    generic_recovery = [
        {
            "tool_name": "database_catalog",
            "effect": "discover_visible_schemas_tables_keys_and_privileges",
        },
        {
            "tool_name": "database_schema",
            "effect": "inspect_physical_columns_constraints_indexes_and_rls",
        },
        {
            "tool_name": "database_query",
            "effect": "execute_ai_authored_read_only_sql",
        },
        {
            "tool_name": "database_execute",
            "effect": "execute_ai_authored_database_write_with_optional_readback",
        },
        {
            "tool_name": "generic_data_resources",
            "effect": "discover_registered_resources",
        },
        {
            "tool_name": "generic_data_resolve",
            "effect": "resolve_canonical_resource_identity",
        },
        {
            "tool_name": "generic_data_observe",
            "effect": "observe_related_world",
        },
        {
            "tool_name": "generic_data_schema",
            "effect": "inspect_registered_fields_relations_and_invariants",
        },
        {
            "tool_name": "generic_data_query",
            "effect": "read_registered_tenant_data",
        },
        {
            "tool_name": "generic_data_mutate",
            "effect": "preview_or_commit_registered_direct_fields",
        },
    ]
    available_capabilities = list(
        {item["tool_name"]: item for item in [*declared_recovery, *generic_recovery]}.values()
    )
    return {
        "schema": "warehouse.atomic-recovery.v1",
        "decision_owner": "auto_runtime",
        "workflow_prescribed": False,
        "failed_capability": (entry or {}).get("tool_name"),
        "semantic_contract": semantic_contract,
        "attempted_arguments": _redacted_values(entry or {}, values or {}),
        "database_fallback": {
            "mode": "company_ai_database_runtime",
            "decision_owner": "auto_runtime",
            "raw_sql_exposed": True,
            "physical_schema_exposed": True,
            "table_headers_exposed": True,
            "row_values_exposed": True,
            "write_sql_exposed": True,
            "database_identity": "current_company_ai",
            "tenant_selector_exposed": False,
        },
        "available_capabilities": available_capabilities,
        "constraints": [
            "execute_as_current_company_ai_database_identity",
            "let_postgresql_privileges_rls_constraints_and_transactions_decide_authority",
            "preserve_canonical_resource_identity_when_one_exists",
            "never_assert_external_reality_from_a_database_write_alone",
            "use_a_specialized_adapter_for_external_effects_or_immutable_evidence",
        ],
    }


# Retain the private name for callers/tests from the original boundary while
# making the recovery packet reusable by the authenticated HTTP fallback.
_atomic_recovery_contract = atomic_recovery_contract


async def _dispatch_async(
    entry: Mapping[str, Any],
    actor: ActorContext,
    values: Mapping[str, object],
    *,
    origin: str,
) -> object:
    """Invoke the registered API contract inside the current ASGI process."""

    # Imported lazily because ``app.main`` imports the API router, which imports
    # this executor.  At execution time application construction is complete.
    from app.api.deps import internal_actor_scope
    from app.main import app

    method, path, body = legacy_catalog.build_request(dict(entry), dict(values))
    settings = get_settings()
    token = create_access_token(
        settings=settings,
        user_id=actor.user_id,
        tenant_id=actor.tenant_id,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": str(uuid4()),
        "X-Warehouse-Tool-Name": str(entry["tool_name"]),
        "X-Warehouse-Execution-Origin": origin,
    }
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    with internal_actor_scope(actor):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://warehouse.internal",
            timeout=30.0,
        ) as client:
            response = await client.request(
                str(method),
                str(path),
                headers=headers,
                json=body,
            )
    if response.status_code == 204:
        payload: object = None
    else:
        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text[:4000]}
    if response.status_code >= 400:
        raise CommandAdapterError(response.status_code, payload)
    return payload


def _dispatch(
    entry: Mapping[str, Any],
    actor: ActorContext,
    values: Mapping[str, object],
    *,
    origin: str,
) -> object:
    if verified_adapter_ready(entry):
        try:
            return execute_verified_adapter(
                entry,
                actor,
                values,
                origin=origin,
            )
        except HTTPException as exc:
            raise CommandAdapterError(
                exc.status_code,
                {"detail": exc.detail},
            ) from exc
    coroutine = _dispatch_async(entry, actor, values, origin=origin)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    # The public FastAPI handlers are synchronous and normally have no running
    # loop.  This fallback keeps the executor safe for async unit/integration
    # callers without nesting ``asyncio.run`` in their loop.
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coroutine).result()


def _audit(
    actor: ActorContext,
    entry: Mapping[str, Any],
    *,
    origin: str,
    status: str,
    values: Mapping[str, object],
    response: Mapping[str, object],
) -> str:
    return command_audit_writer().record(
        actor=actor,
        command=str(entry["command"]),
        tool_name=str(entry["tool_name"]),
        origin=origin,
        status=status,
        request={"arguments": _redacted_values(entry, values)},
        response=_redacted_response(entry, response),
    )


def _execute_entry(
    entry: Mapping[str, Any],
    actor: ActorContext,
    values: Mapping[str, object],
    *,
    origin: str,
    enforce_actor_permissions: bool = True,
    confirmation_verified: bool = False,
) -> dict[str, object]:
    started = perf_counter()
    command = str(entry["command"])
    tool_name = str(entry["tool_name"])
    writes = bool(entry["writes"])
    risk = str(entry["risk"])
    if enforce_actor_permissions and not is_authorized(dict(entry), actor.permissions):
        envelope = _envelope(
            ok=False,
            command=command,
            tool_name=tool_name,
            status="denied",
            writes=writes,
            risk=risk,
            error="You do not hold the required capability for this command",
            elapsed_ms=round((perf_counter() - started) * 1000),
        )
        execution_id = _audit(
            actor, entry, origin=origin, status="denied", values=values, response=envelope
        )
        envelope["execution_id"] = execution_id
        return envelope

    state = availability(dict(entry))
    if state != "active":
        reason = (
            "A capability concept exists, but no truthful domain adapter is mounted"
            if state == "awaiting_domain_adapter"
            else "Command contract is not executable"
        )
        capability_gap = None
        if state == "awaiting_domain_adapter":
            try:
                from app.services.generic_data import record_missing_capability_gap

                capability_gap = record_missing_capability_gap(
                    actor,
                    entry=dict(entry),
                    arguments=dict(values),
                    origin=origin,
                    reason=reason,
                )
            except Exception:
                # Gap telemetry is best effort and must never turn a truthful
                # unavailable result into an execution exception.
                capability_gap = None
        envelope = _envelope(
            ok=False,
            command=command,
            tool_name=tool_name,
            status=state,
            writes=writes,
            risk=risk,
            error=reason,
            hint=(
                "Auto Runtime may inspect the physical database, query or write through "
                "the current company AI identity, use semantic resources, choose another "
                "atomic ability, or report the capability gap."
            ),
            data={
                "execution_kind": execution_kind(dict(entry)),
                "transitional_projection_authoritative": False,
                "capability_gap": capability_gap,
                "atomic_recovery": atomic_recovery_contract(entry, values),
            },
            elapsed_ms=round((perf_counter() - started) * 1000),
        )
        audit_status = (
            state
            if state in {"awaiting_domain_adapter", "invalid_contract"}
            else "invalid_contract"
        )
        execution_id = _audit(
            actor,
            entry,
            origin=origin,
            status=audit_status,
            values=values,
            response=envelope,
        )
        envelope["execution_id"] = execution_id
        return envelope

    confirmation = legacy_catalog.confirmation_contract(dict(entry))
    if writes and confirmation["mode"] != "direct" and not confirmation_verified:
        envelope = _envelope(
            ok=False,
            command=command,
            tool_name=tool_name,
            status="confirmation_required",
            writes=writes,
            risk=risk,
            error="This command requires its registered confirmation workflow",
            hint=(f"confirmation mode: {confirmation['mode']}; adapter: {confirmation['adapter']}"),
            data={
                "confirmation_policy": confirmation,
                "arguments": _redacted_values(entry, values),
            },
            elapsed_ms=round((perf_counter() - started) * 1000),
        )
        execution_id = _audit(
            actor,
            entry,
            origin=origin,
            status="confirmation_required",
            values=values,
            response=envelope,
        )
        envelope["execution_id"] = execution_id
        return envelope

    try:
        data = _dispatch(entry, actor, values, origin=origin)
    except CommandAdapterError as exc:
        envelope = _envelope(
            ok=False,
            command=command,
            tool_name=tool_name,
            status="target_rejected",
            writes=writes,
            risk=risk,
            data={
                "http_status": exc.status_code,
                "response": exc.payload,
                "atomic_recovery": atomic_recovery_contract(entry, values),
            },
            error=f"Target business API rejected the command (HTTP {exc.status_code})",
            elapsed_ms=round((perf_counter() - started) * 1000),
        )
        execution_id = _audit(
            actor,
            entry,
            origin=origin,
            status="target_rejected",
            values=values,
            response=envelope,
        )
        envelope["execution_id"] = execution_id
        return envelope
    except Exception as exc:  # pragma: no cover - exercised at the HTTP boundary
        envelope = _envelope(
            ok=False,
            command=command,
            tool_name=tool_name,
            status="failed",
            writes=writes,
            risk=risk,
            data={"atomic_recovery": atomic_recovery_contract(entry, values)},
            error="Command adapter failed",
            elapsed_ms=round((perf_counter() - started) * 1000),
        )
        execution_id = _audit(
            actor,
            entry,
            origin=origin,
            status="failed",
            values=values,
            response={**envelope, "failure_type": type(exc).__name__},
        )
        envelope["execution_id"] = execution_id
        return envelope

    safe_data, credentials = _extract_one_time_credentials(entry, data)
    envelope = _envelope(
        ok=True,
        command=command,
        tool_name=tool_name,
        status="succeeded",
        writes=writes,
        risk=risk,
        data=safe_data,
        elapsed_ms=round((perf_counter() - started) * 1000),
    )
    if credentials:
        envelope["credentials"] = credentials
    execution_id = _audit(
        actor, entry, origin=origin, status="succeeded", values=values, response=envelope
    )
    envelope["execution_id"] = execution_id
    return envelope


def _local_command(actor: ActorContext, line: str) -> dict[str, object] | None:
    normalized = line.strip()
    if normalized in {"help", "?"}:
        return _envelope(
            ok=True,
            command="help",
            tool_name="terminal_help",
            status="succeeded",
            writes=False,
            risk="low",
            data={"commands": command_catalogue(actor, include_unavailable=True)},
        )
    if normalized.startswith("capabilities"):
        query = normalized.removeprefix("capabilities").strip().lower()
        commands = command_catalogue(actor, include_unavailable=True)
        if query:
            commands = [
                item
                for item in commands
                if query in str(item["command"]).lower()
                or query in str(item["description"]).lower()
            ]
        return _envelope(
            ok=True,
            command="capabilities",
            tool_name="terminal_capabilities",
            status="succeeded",
            writes=False,
            risk="low",
            data={"commands": commands},
        )
    return None


def execute_cli_line(
    actor: ActorContext, line: str, *, origin: str = "terminal"
) -> dict[str, object]:
    """Parse and execute one human-terminal command through the same adapter path as AI."""
    local = _local_command(actor, line)
    if local is not None:
        return local
    try:
        entry, values = legacy_catalog.parse_line(line)
    except legacy_catalog.CommandError as exc:
        return _envelope(
            ok=False,
            command="",
            tool_name="",
            status="invalid",
            writes=False,
            risk="low",
            error=str(exc),
            usage=exc.usage,
            hint=exc.hint,
            data={"atomic_recovery": atomic_recovery_contract(None, {"line": line})},
        )
    return _execute_entry(entry, actor, values, origin=origin)


def execute_tool_call(
    actor: ActorContext, tool_name: str, arguments: Mapping[str, object]
) -> dict[str, object]:
    """Run a model tool call without giving the model route or database control."""
    entry = entry_by_tool_name(tool_name)
    if entry is None:
        return _envelope(
            ok=False,
            command="",
            tool_name=tool_name,
            status="unknown_tool",
            writes=False,
            risk="low",
            error="Tool is not registered in the tenant command catalogue",
        )
    try:
        values = legacy_catalog.values_from_tool_args(entry, dict(arguments))
    except legacy_catalog.CommandError as exc:
        return _envelope(
            ok=False,
            command=entry["command"],
            tool_name=tool_name,
            status="invalid_arguments",
            writes=bool(entry["writes"]),
            risk=str(entry["risk"]),
            error=str(exc),
            usage=exc.usage,
            hint=exc.hint,
            data={"atomic_recovery": atomic_recovery_contract(entry, arguments)},
        )
    return _execute_entry(entry, actor, values, origin="ai_tool")


def execute_api_contract(
    actor: ActorContext,
    entry: Mapping[str, Any],
    values: Mapping[str, object],
    *,
    origin: str = "api",
) -> dict[str, object]:
    """Execute an authenticated retained HTTP contract through this boundary."""

    return _execute_entry(entry, actor, values, origin=origin)


def execute_manual_action(
    actor: ActorContext, tool_name: str, arguments: Mapping[str, object]
) -> dict[str, object]:
    """Run a schema-generated manual form through the shared command boundary."""
    entry = entry_by_tool_name(tool_name)
    if entry is None:
        platform_entry = entry_by_tool_name(tool_name, platform=True)
        if platform_entry is not None:
            return _envelope(
                ok=False,
                command=str(platform_entry["command"]),
                tool_name=tool_name,
                status="requires_l11_governance",
                writes=bool(platform_entry["writes"]),
                risk=str(platform_entry["risk"]),
                error="Platform actions cannot execute inside a company session",
            )
        return _envelope(
            ok=False,
            command="",
            tool_name=tool_name,
            status="unknown_tool",
            writes=False,
            risk="low",
            error="Action is not registered in the shared capability catalogue",
        )
    try:
        values = legacy_catalog.values_from_tool_args(entry, dict(arguments))
    except legacy_catalog.CommandError as exc:
        return _envelope(
            ok=False,
            command=str(entry["command"]),
            tool_name=tool_name,
            status="invalid_arguments",
            writes=bool(entry["writes"]),
            risk=str(entry["risk"]),
            error=str(exc),
            usage=exc.usage,
            hint=exc.hint,
            data={"atomic_recovery": atomic_recovery_contract(entry, arguments)},
        )
    return _execute_entry(entry, actor, values, origin="manual_ui")


def execute_runtime_tool_call(
    actor: ActorContext,
    tool_name: str,
    arguments: Mapping[str, object],
    *,
    execution_context: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Execute an internally selected capability under the company AI identity.

    The Runtime, unlike a human terminal session, may reason across the whole
    current-company authority map.  This path therefore does not project the
    current human's permission subset onto the AI.  It is intentionally not an
    HTTP route: callers cannot manufacture this trusted decision boundary.
    Adapter availability, typed validation, tenant RLS and audit recording
    still apply unchanged.
    """
    entry = entry_by_tool_name(tool_name)
    if entry is None:
        platform_entry = entry_by_tool_name(tool_name, platform=True)
        if platform_entry is not None:
            return _envelope(
                ok=False,
                command=str(platform_entry["command"]),
                tool_name=tool_name,
                status="requires_l11_governance",
                writes=bool(platform_entry["writes"]),
                risk=str(platform_entry["risk"]),
                error="The selected platform capability is not connected to this tenant Runtime",
            )
        return _envelope(
            ok=False,
            command="",
            tool_name=tool_name,
            status="unknown_tool",
            writes=False,
            risk="unknown",
            error="Unknown capability gene",
        )
    try:
        values = legacy_catalog.values_from_tool_args(entry, dict(arguments))
    except ValueError as exc:
        return _envelope(
            ok=False,
            command=str(entry["command"]),
            tool_name=tool_name,
            status="invalid_arguments",
            writes=bool(entry["writes"]),
            risk=str(entry["risk"]),
            error=str(exc),
            data={"atomic_recovery": atomic_recovery_contract(entry, arguments)},
        )
    if (
        tool_name
        in {
            "generic_data_mutate",
            "database_query",
            "database_execute",
        }
        and execution_context
    ):
        if execution_context.get("run_id"):
            values["body.run_id"] = execution_context["run_id"]
        if execution_context.get("conversation_id"):
            values["body.conversation_id"] = execution_context["conversation_id"]
    return _execute_entry(
        entry,
        actor,
        values,
        origin="auto_runtime",
        enforce_actor_permissions=False,
    )


def execute_confirmed_runtime_tool_call(
    actor: ActorContext, tool_name: str, arguments: Mapping[str, object]
) -> dict[str, object]:
    """Execute one previously persisted and Passkey-confirmed Runtime action.

    This entry point is deliberately not exposed as an HTTP route. The caller
    must first bind and consume a one-time confirmation grant; typed catalogue
    validation, tenant RLS, native API dispatch and redacted audit remain the
    same as the ordinary Auto Runtime path.
    """

    entry = entry_by_tool_name(tool_name)
    if entry is None:
        return _envelope(
            ok=False,
            command="",
            tool_name=tool_name,
            status="unknown_tool",
            writes=False,
            risk="unknown",
            error="Unknown capability gene",
        )
    try:
        values = legacy_catalog.values_from_tool_args(entry, dict(arguments))
    except (legacy_catalog.CommandError, ValueError) as exc:
        return _envelope(
            ok=False,
            command=str(entry["command"]),
            tool_name=tool_name,
            status="invalid_arguments",
            writes=bool(entry["writes"]),
            risk=str(entry["risk"]),
            error=str(exc),
            data={"atomic_recovery": atomic_recovery_contract(entry, arguments)},
        )
    return _execute_entry(
        entry,
        actor,
        values,
        origin="auto_runtime",
        enforce_actor_permissions=False,
        confirmation_verified=True,
    )
