"""Authenticated, fail-closed boundary for unmigrated catalogue contracts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import current_actor
from app.core.config import Settings, get_settings
from app.terminal.catalog import availability
from app.terminal.executor import atomic_recovery_contract, execute_api_contract
from app.terminal.gateway import match_contract

router = APIRouter(tags=["terminal-capability-gateway"])
_bearer = HTTPBearer(auto_error=False)


@router.api_route(
    "/api/{capability_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
    response_model=None,
)
async def catalogue_capability_gateway(
    capability_path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> object:
    path = f"/api/{capability_path}"
    tool_name = request.headers.get("X-Warehouse-Tool-Name")
    matched = match_contract(request.method, path, tool_name=tool_name)
    if matched is None:
        return JSONResponse(
            status_code=501,
            content={
                "available": False,
                "status": "not_implemented",
                "reason": (
                    "catalogue_contract_mismatch" if tool_name else "api_contract_not_migrated"
                ),
                "path": path,
            },
        )
    actor = current_actor(request=request, credentials=credentials, settings=settings)
    body: dict[str, object] = {}
    if request.method != "GET":
        try:
            candidate = await request.json()
        except ValueError:
            candidate = {}
        if isinstance(candidate, dict):
            body = candidate
    query = dict(request.query_params)
    origin = request.headers.get("X-Warehouse-Execution-Origin") or "api"
    arguments = {**matched.path_params, **query, **body}
    if availability(matched.entry) == "active":
        values: dict[str, object] = {}
        for parameter in matched.entry.get("params") or []:
            destination = str(parameter.get("dest") or "")
            scope, separator, key = destination.partition(".")
            source = matched.path_params if scope == "path" else query if scope == "query" else body
            if scope == "body" and not separator:
                value: object = body
            elif key in source:
                value = source[key]
            else:
                value = parameter.get("default")
            if value is not None:
                values[destination] = value
        return execute_api_contract(
            actor,
            matched.entry,
            values,
            origin=origin,
        )
    reason = "Catalogue contract has no mounted truthful domain adapter"
    try:
        from app.services.generic_data import record_missing_capability_gap

        gap = record_missing_capability_gap(
            actor,
            entry=dict(matched.entry),
            arguments=arguments,
            origin=origin,
            reason=reason,
        )
    except Exception:
        gap = None
    return JSONResponse(
        status_code=501,
        content={
            "ok": False,
            "available": False,
            "status": "awaiting_domain_adapter",
            "reason": "capability_gap",
            "tool_name": str(matched.entry["tool_name"]),
            "execution_kind": "capability_gap",
            "transitional_projection_authoritative": False,
            "capability_gap": gap,
            "atomic_recovery": atomic_recovery_contract(
                matched.entry,
                arguments,
            ),
        },
    )
