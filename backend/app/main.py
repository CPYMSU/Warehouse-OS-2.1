from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.compat import router as compatibility_router
from app.api.full_stack import router as full_stack_router
from app.api.router import router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.3.0", docs_url="/docs", redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Tenant-Slug"],
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


# The full-stack router must be first. It implements the response envelopes and
# write workflows used by the retained clients. Foundation and compatibility
# routers remain available for routes that have already moved to final schemas.
app.include_router(full_stack_router)
app.include_router(router)
app.include_router(compatibility_router)


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
def unmigrated_api_contract(path: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "available": False,
            "status": "not_implemented",
            "reason": "api_contract_not_migrated",
            "path": f"/api/{path}",
        },
    )


frontend_directory = Path(__file__).resolve().parents[2] / "frontend" / "v2"
if frontend_directory.is_dir():
    app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
