"""Catalogue contract matcher for capabilities awaiting a domain adapter.

The matcher remains useful for discovery and truthful gap receipts.  The old
generic PostgreSQL projection executor was intentionally disabled: persisting
an arbitrary command-shaped document is not proof that its business effect
happened.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from app.terminal import legacy_catalog

if TYPE_CHECKING:
    from app.api.deps import ActorContext

_SUPPORTED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
@dataclass(frozen=True)
class ContractMatch:
    """One exact tenant command contract matched to a concrete HTTP request."""

    entry: dict[str, Any]
    path_params: dict[str, str]


def _path_parameter_names(path: str) -> frozenset[str]:
    return frozenset(re.findall(r"\{([^{}]+)\}", path))


def gateway_contract_ready(entry: dict[str, Any]) -> bool:
    """Return whether a catalogue row is structurally routable by the gateway."""

    method = str(entry.get("api_method") or "").upper()
    path = str(entry.get("api_path") or "")
    params = entry.get("params")
    if method not in _SUPPORTED_METHODS or not path.startswith("/api/"):
        return False
    if not isinstance(params, list):
        return False
    destinations: set[str] = set()
    for parameter in params:
        if not isinstance(parameter, dict):
            return False
        destination = str(parameter.get("dest") or "")
        scope, separator, key = destination.partition(".")
        if scope not in {"path", "query", "body"}:
            return False
        if scope != "body" and (not separator or not key):
            return False
        if scope == "body" and separator and not key:
            return False
        destinations.add(destination)
    path_destinations = {
        destination.removeprefix("path.")
        for destination in destinations
        if destination.startswith("path.")
    }
    return path_destinations == set(_path_parameter_names(path))


def _compile_path(path: str) -> re.Pattern[str]:
    cursor = 0
    chunks: list[str] = ["^"]
    for match in re.finditer(r"\{([^{}]+)\}", path):
        chunks.append(re.escape(path[cursor : match.start()]))
        chunks.append(f"(?P<{match.group(1)}>[^/?]+)")
        cursor = match.end()
    chunks.extend((re.escape(path[cursor:]), "$"))
    return re.compile("".join(chunks))


@lru_cache(maxsize=1)
def _contracts() -> tuple[tuple[dict[str, Any], re.Pattern[str]], ...]:
    rows = [
        (entry, _compile_path(str(entry["api_path"])))
        for entry in legacy_catalog.COMMANDS
        if gateway_contract_ready(entry)
    ]
    rows.sort(
        key=lambda row: (
            -len(str(row[0]["api_path"]).replace("{", "").replace("}", "")),
            str(row[0]["tool_name"]),
        )
    )
    return tuple(rows)


def match_contract(
    method: str,
    path: str,
    *,
    tool_name: str | None = None,
) -> ContractMatch | None:
    """Resolve a request without allowing its caller to select another route."""

    normalized_method = method.upper()
    if tool_name:
        entry = next(
            (
                candidate
                for candidate in legacy_catalog.COMMANDS
                if candidate["tool_name"] == tool_name
            ),
            None,
        )
        if (
            entry is None
            or str(entry["api_method"]).upper() != normalized_method
            or not gateway_contract_ready(entry)
        ):
            return None
        matched = _compile_path(str(entry["api_path"])).fullmatch(path)
        return (
            ContractMatch(entry=entry, path_params=matched.groupdict())
            if matched
            else None
        )

    candidates: list[ContractMatch] = []
    for entry, pattern in _contracts():
        if str(entry["api_method"]).upper() != normalized_method:
            continue
        matched = pattern.fullmatch(path)
        if matched:
            candidates.append(
                ContractMatch(entry=entry, path_params=matched.groupdict())
            )
    if not candidates:
        return None
    # Three historical pairs share a method/path.  Direct API callers must name
    # the tool rather than letting registry order silently choose a mutation.
    unique_tools = {str(candidate.entry["tool_name"]) for candidate in candidates}
    return candidates[0] if len(unique_tools) == 1 else None


def execute_gateway_contract(
    actor: ActorContext,
    match: ContractMatch,
    *,
    query: dict[str, object] | None = None,
    body: dict[str, object] | None = None,
    origin: str = "api",
) -> dict[str, object]:
    """Retained API name that now fails closed without touching business data."""

    del actor, query, body
    return {
        "ok": False,
        "available": False,
        "status": "awaiting_domain_adapter",
        "reason": "transitional_projection_disabled",
        "tool_name": str(match.entry["tool_name"]),
        "execution_kind": "capability_gap",
        "origin": origin,
        "transitional_projection_authoritative": False,
    }
