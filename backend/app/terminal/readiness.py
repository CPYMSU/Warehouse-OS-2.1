"""Runtime truth registry for catalogue capability adapters.

The imported command catalogue is a discovery vocabulary.  A structurally
valid method/path pair is not proof that a business adapter exists.  This
module records the concrete FastAPI routes mounted before the transitional
catch-all gateway and lets the catalogue expose that distinction without
hard-coding one business-tool allowlist.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from threading import RLock
from typing import Any

_PATH_PARAMETER_RE = re.compile(r"\{[^{}]+\}")
_lock = RLock()
_native_route_signatures: frozenset[tuple[str, str]] = frozenset()
_native_route_handlers: dict[tuple[str, str], tuple[str, ...]] = {}
_configured = False


def _normalized_path(path: object) -> str:
    """Compare semantic route shapes without depending on parameter names."""

    return _PATH_PARAMETER_RE.sub("{}", str(path or ""))


def _walk_routes(routes: Iterable[object]) -> Iterable[object]:
    """Flatten FastAPI's lazy included-router wrappers without importing app."""

    for route in routes:
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            yield from _walk_routes(getattr(original_router, "routes", ()))
            continue
        nested = getattr(route, "routes", None)
        if nested is not None and getattr(route, "path", None) is None:
            yield from _walk_routes(nested)
            continue
        if getattr(route, "path", None):
            yield route


def configure_native_capability_routes(app: Any) -> None:
    """Snapshot real routes before the generic compatibility gateway is mounted.

    ``app.main`` calls this after every explicit domain router is included and
    before the catalogue catch-all.  Adding a normal FastAPI route therefore
    activates its matching capability automatically; no per-command readiness
    branch is required.
    """

    handlers: dict[tuple[str, str], set[str]] = {}
    for route in _walk_routes(getattr(app, "routes", ())):
        path = _normalized_path(getattr(route, "path", ""))
        endpoint = getattr(route, "endpoint", None)
        handler = (
            f"{getattr(endpoint, '__module__', '<unknown>')}."
            f"{getattr(endpoint, '__qualname__', getattr(endpoint, '__name__', '<unknown>'))}"
        )
        for method in getattr(route, "methods", ()) or ():
            signature = (str(method).upper(), path)
            handlers.setdefault(signature, set()).add(handler)
    signatures = frozenset(handlers)
    handler_snapshot = {
        signature: tuple(sorted(names)) for signature, names in handlers.items()
    }
    global _configured, _native_route_handlers, _native_route_signatures
    with _lock:
        _native_route_signatures = signatures
        _native_route_handlers = handler_snapshot
        _configured = True


def native_adapter_ready(entry: dict[str, object]) -> bool:
    """Return whether one catalogue gene has a concrete mounted adapter."""

    signature = (
        str(entry.get("api_method") or "").upper(),
        _normalized_path(entry.get("api_path")),
    )
    with _lock:
        return _configured and signature in _native_route_signatures


def native_adapter_evidence(entry: dict[str, object]) -> dict[str, object] | None:
    """Return the concrete pre-gateway handlers proving native readiness."""

    signature = (
        str(entry.get("api_method") or "").upper(),
        _normalized_path(entry.get("api_path")),
    )
    with _lock:
        if not _configured or signature not in _native_route_signatures:
            return None
        return {
            "method": signature[0],
            "contract_path": str(entry.get("api_path") or ""),
            "normalized_path": signature[1],
            "handlers": list(_native_route_handlers.get(signature) or ()),
            "captured_before_catch_all": True,
        }


def readiness_snapshot() -> dict[str, object]:
    """Expose non-secret diagnostics for tests and runtime status surfaces."""

    from app.terminal.adapters import verified_adapter_snapshot

    with _lock:
        return {
            "configured": _configured,
            "native_route_signature_count": len(_native_route_signatures),
            "native_route_handler_count": sum(
                len(handlers) for handlers in _native_route_handlers.values()
            ),
            "verified_registry": verified_adapter_snapshot(),
        }
