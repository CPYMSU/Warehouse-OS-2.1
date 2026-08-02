"""Authenticated fallback for catalogue-backed tenant API contracts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import current_actor
from app.core.config import Settings, get_settings
from app.terminal.gateway import execute_gateway_contract, match_contract

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
                    "catalogue_contract_mismatch"
                    if tool_name
                    else "api_contract_not_migrated"
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
    return execute_gateway_contract(
        actor,
        matched,
        query=query,
        body=body,
        origin=request.headers.get("X-Warehouse-Execution-Origin") or "api",
    )
