"""Single execution boundary shared by the human terminal and AI tool calls."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import TYPE_CHECKING, Any

from app.terminal import legacy_catalog
from app.terminal.catalog import (
    availability,
    command_catalogue,
    entry_by_tool_name,
    is_authorized,
)
from app.terminal.store import command_audit_writer, warehouse_reader

if TYPE_CHECKING:
    from app.api.deps import ActorContext

_SECRET_PARTS = ("password", "secret", "token", "api_key", "credential", "passkey", "sql")


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


def _actor_payload(actor: ActorContext) -> dict[str, object]:
    return {
        "authenticated": True,
        "tenant": actor.tenant_slug,
        "companies": [{"slug": actor.tenant_slug, "name": actor.tenant_name, "status": "active"}],
        "user": actor.user_payload,
        "permissions": sorted(actor.permissions),
        "is_platform_owner": False,
        "can_apply_company": actor.role_level >= 4,
        "needs_setup": False,
    }


def _dispatch(
    entry: Mapping[str, Any], actor: ActorContext, values: Mapping[str, object]
) -> object:
    tool_name = str(entry["tool_name"])
    if tool_name == "auth_me":
        return _actor_payload(actor)
    if tool_name == "warehouse_list":
        return {"warehouses": warehouse_reader().list_active(actor.tenant_id)}
    raise RuntimeError(f"active adapter is missing: {tool_name}")


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
        response=response,
    )


def _execute_entry(
    entry: Mapping[str, Any],
    actor: ActorContext,
    values: Mapping[str, object],
    *,
    origin: str,
) -> dict[str, object]:
    started = perf_counter()
    command = str(entry["command"])
    tool_name = str(entry["tool_name"])
    writes = bool(entry["writes"])
    risk = str(entry["risk"])
    if not is_authorized(dict(entry), actor.permissions):
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
        envelope = _envelope(
            ok=False,
            command=command,
            tool_name=tool_name,
            status=state,
            writes=writes,
            risk=risk,
            error="Command contract is imported, but its PostgreSQL domain adapter is not ready",
            hint=(
                "This command remains unavailable until its typed domain route, validation, "
                "and tests are migrated."
            ),
            elapsed_ms=round((perf_counter() - started) * 1000),
        )
        execution_id = _audit(
            actor, entry, origin=origin, status=state, values=values, response=envelope
        )
        envelope["execution_id"] = execution_id
        return envelope

    # No mutation is enabled in the foundation.  This is intentionally a
    # second line of defence if a future manifest edit marks a write active
    # before a persistent confirmation workflow is registered.
    if writes:
        raise RuntimeError("an active write command requires a confirmation workflow")

    try:
        data = _dispatch(entry, actor, values)
    except Exception as exc:  # pragma: no cover - exercised at the HTTP boundary
        envelope = _envelope(
            ok=False,
            command=command,
            tool_name=tool_name,
            status="failed",
            writes=writes,
            risk=risk,
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

    envelope = _envelope(
        ok=True,
        command=command,
        tool_name=tool_name,
        status="succeeded",
        writes=writes,
        risk=risk,
        data=data,
        elapsed_ms=round((perf_counter() - started) * 1000),
    )
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
            data={"commands": command_catalogue(actor)},
        )
    if normalized.startswith("capabilities"):
        query = normalized.removeprefix("capabilities").strip().lower()
        commands = command_catalogue(actor)
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
        )
    return _execute_entry(entry, actor, values, origin="ai_tool")
