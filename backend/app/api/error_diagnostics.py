"""Stable, non-secret diagnostics for every hosted-workspace API failure."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("warehouse.api")


def _route_stage(request: Request) -> tuple[str, str, str]:
    path = request.url.path
    method = request.method.upper()
    if "/sources" in path or path.endswith("/source"):
        return (
            "source.upload" if method == "POST" else "source.observe",
            "source",
            "inspect the source archive and upload evidence",
        )
    if path.endswith("/runtime"):
        return (
            "runtime.configure",
            "runtime",
            "correct Runtime detection or explicit Runtime fields",
        )
    if "/deployments" in path:
        if path.endswith("/deployments") and method == "POST":
            return (
                "deployment.request",
                "deployment",
                "correct the request and retry with the same idempotency key",
            )
        if path.endswith("/logs"):
            return (
                "deployment.logs",
                "runtime",
                "observe the deployment event stream and redacted logs",
            )
        return (
            "deployment.observe",
            "deployment",
            "observe the latest event and repair its failed stage",
        )
    if path.startswith("/assets/"):
        return (
            "route.proxy",
            "public_route",
            "verify the active deployment and public route evidence",
        )
    if "/database" in path or "/data/" in path:
        return (
            "database.access",
            "database",
            "verify the database binding, schema and record version",
        )
    if "/fabric" in path:
        return (
            "infrastructure.apply",
            "infrastructure",
            "inspect the resource action and provider observation",
        )
    if "/keys" in path:
        return (
            "credential.manage",
            "credential",
            "use the active primary workspace key and retry",
        )
    if path.endswith("/quota") or "workspace-quota" in path:
        return (
            "storage.allocate",
            "storage",
            "observe usage and request sufficient capacity",
        )
    if path.startswith("/api/hosting/v2"):
        return (
            "hosting.session",
            "hosting",
            "resume the same session and inspect its diagnostic event",
        )
    return "api.request", "api", "correct the request using the returned detail"


def _detail_values(
    detail: object,
) -> tuple[str | None, str | None, str | None, bool | None]:
    if not isinstance(detail, dict):
        return None, str(detail) if detail not in (None, "") else None, None, None
    reason = detail.get("reason") or detail.get("error_code")
    message = detail.get("message") or detail.get("detail")
    next_action = detail.get("next_action")
    retryable = detail.get("retryable")
    return (
        str(reason) if reason not in (None, "") else None,
        str(message) if message not in (None, "") else None,
        str(next_action) if next_action not in (None, "") else None,
        bool(retryable) if retryable is not None else None,
    )


def _diagnostic(
    request: Request,
    *,
    status_code: int,
    detail: object,
    fallback_code: str,
) -> dict[str, object]:
    stage, component, default_action = _route_stage(request)
    reason, message, next_action, explicit_retryable = _detail_values(detail)
    retryable = explicit_retryable
    if retryable is None:
        retryable = status_code in {408, 409, 423, 425, 429, 500, 502, 503, 504, 507}
    return {
        "stage": stage,
        "component": component,
        "error_code": reason or fallback_code,
        "message": message or "The requested operation could not be completed",
        "http_status": status_code,
        "retryable": retryable,
        "next_action": next_action or default_action,
        "request_id": getattr(request.state, "request_id", None),
        "method": request.method,
        "path": request.url.path,
        "raw_reasoning_exposed": False,
    }


def install_error_diagnostics(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        diagnostic = _diagnostic(
            request,
            status_code=exc.status_code,
            detail=exc.detail,
            fallback_code=f"http_{exc.status_code}",
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(
                {"detail": exc.detail, "diagnostic": diagnostic}
            ),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        diagnostic = _diagnostic(
            request,
            status_code=422,
            detail={
                "reason": "request_validation_failed",
                "message": "One or more fields do not match the API contract",
                "next_action": "correct the listed fields without changing the target",
                "retryable": True,
            },
            fallback_code="request_validation_failed",
        )
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                {"detail": exc.errors(), "diagnostic": diagnostic}
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled API failure request_id=%s method=%s path=%s",
            getattr(request.state, "request_id", None),
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        diagnostic = _diagnostic(
            request,
            status_code=500,
            detail={
                "reason": "unexpected_server_error",
                "message": "The server stopped this stage without claiming success",
                "next_action": "use the request ID to inspect and retry only this stage",
                "retryable": True,
            },
            fallback_code="unexpected_server_error",
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Unexpected server error",
                "diagnostic": diagnostic,
            },
        )
