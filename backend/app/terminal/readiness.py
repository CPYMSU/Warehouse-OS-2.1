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

    signatures: set[tuple[str, str]] = set()
    for route in _walk_routes(getattr(app, "routes", ())):
        path = _normalized_path(getattr(route, "path", ""))
        for method in getattr(route, "methods", ()) or ():
            signatures.add((str(method).upper(), path))
    global _configured, _native_route_signatures
    with _lock:
        _native_route_signatures = frozenset(signatures)
        _configured = True


def native_adapter_ready(entry: dict[str, object]) -> bool:
    """Return whether one catalogue gene has a concrete mounted adapter."""

    signature = (
        str(entry.get("api_method") or "").upper(),
        _normalized_path(entry.get("api_path")),
    )
    with _lock:
        return _configured and signature in _native_route_signatures


def readiness_snapshot() -> dict[str, object]:
    """Expose non-secret diagnostics for tests and runtime status surfaces."""

    from app.terminal.adapters import verified_adapter_snapshot

    with _lock:
        return {
            "configured": _configured,
            "native_route_signature_count": len(_native_route_signatures),
            "verified_registry": verified_adapter_snapshot(),
        }
