from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.compat import router as compatibility_router
from app.api.router import router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0", docs_url="/docs", redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Warehouse-Backend"] = "fastapi-postgresql"
    return response


@app.get("/health", tags=["system"])
def liveness() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "warehouse-os-api"})


app.include_router(router)
app.include_router(compatibility_router)


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
def unmigrated_api_contract(path: str) -> JSONResponse:
    """Keep API requests out of the SPA/static-file fallback.

    A missing backend contract must be an explicit JSON 501, never a misleading
    static-file 404/405. The frontend can then render a truthful unavailable
    state and the contract test can identify the exact route still to migrate.
    """
    return JSONResponse(
        status_code=501,
        content={
            "available": False,
            "status": "not_implemented",
            "reason": "api_contract_not_migrated",
            "path": f"/api/{path}",
        },
    )


# In local development, serve the versioned web client from the same origin as
# the API. This keeps authentication requests inside the tenant API boundary
# and avoids a separate, stale frontend port. The catch-all API route above must
# remain before this mount so /api requests can never be swallowed by StaticFiles.
frontend_directory = Path(__file__).resolve().parents[2] / "frontend" / "v2"
if frontend_directory.is_dir():
    app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
