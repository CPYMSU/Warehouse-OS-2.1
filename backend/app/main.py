from __future__ import annotations

from mimetypes import guess_type
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import digital_assets as digital_assets_module
from app.api import hosted_runtime_gateway as hosted_runtime_gateway_module
from app.api import intelligent_hosting as intelligent_hosting_module
from app.api.browser_runtime import router as browser_runtime_router
from app.api.capability_gateway import router as capability_gateway_router
from app.api.cluster_status import router as cluster_status_router
from app.api.compat import router as compatibility_router
from app.api.confirmation_actions import router as confirmation_actions_router
from app.api.database_browser_gateway import router as database_browser_gateway_router
from app.api.digital_assets import router as digital_asset_router
from app.api.error_diagnostics import install_error_diagnostics
from app.api.full_stack import router as full_stack_router
from app.api.generic_data import router as generic_data_router
from app.api.hosted_gateway_compat import rewrite_cookie_path
from app.api.hosted_runtime_gateway import router as hosted_runtime_gateway_router
from app.api.hosting_session_extension_compat import (
    router as hosting_session_extension_compat_router,
)
from app.api.intelligent_hosting import router as intelligent_hosting_router
from app.api.intelligent_hosting_compat import router as intelligent_hosting_compat_router
from app.api.lighthouse_federation import router as lighthouse_federation_router
from app.api.research import router as research_router
from app.api.router import router
from app.api.shield import router as shield_router
from app.api.task_collaboration import router as task_collaboration_router
from app.api.workspace_auth_compat import authenticate_workspace_key
from app.api.workspace_autonomy import router as workspace_autonomy_router
from app.api.workspace_company_compat import router as workspace_company_compat_router
from app.api.workspace_provision_compat import router as workspace_provision_compat_router
from app.api.workspace_v1_compat import router as workspace_v1_compat_router
from app.core.config import get_settings
from app.services.database_browser_gateway import origin_is_allowed
from app.terminal.readiness import configure_native_capability_routes

# Keep the original modules as stable extension points. Their runtime globals are
# upgraded, so existing dependency overrides and plugins still reach the new
# autonomous key verifier instead of being bypassed by a parallel implementation.
digital_assets_module.guess_type = guess_type
intelligent_hosting_module.authenticate_workspace_key = authenticate_workspace_key
hosted_runtime_gateway_module._REQUEST_EXCLUDED = (
    hosted_runtime_gateway_module._REQUEST_EXCLUDED - {"host"}
)
hosted_runtime_gateway_module._rewrite_cookie = rewrite_cookie_path

settings = get_settings()
app = FastAPI(title=settings.app_name, version="2.1.0", docs_url="/docs", redoc_url=None)
install_error_diagnostics(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Tenant-Slug",
        "X-Warehouse-Tool-Name",
        "X-Warehouse-Execution-Origin",
        "Idempotency-Key",
        "Content-SHA256",
    ],
)


@app.middleware("http")
async def request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Warehouse-Backend"] = "fastapi-postgresql"
    return response


@app.middleware("http")
async def database_gateway_cors(request: Request, call_next):
    """Apply the configured exact-origin policy to browser database routes."""

    prefix = "/api/database-gateway/v1/projects/"
    origin = request.headers.get("origin")
    if not request.url.path.startswith(prefix) or not origin:
        return await call_next(request)
    project_key = request.url.path.removeprefix(prefix).split("/", 1)[0]
    allowed = origin_is_allowed(project_key, origin, settings=settings)
    if request.method == "OPTIONS":
        if not allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": "Browser origin is not allowed"},
            )
        response: Response = Response(status_code=204)
    else:
        response = await call_next(request)
    if allowed:
        response.headers["Access-Control-Allow-Origin"] = origin.rstrip("/")
        response.headers["Access-Control-Allow-Methods"] = "GET, PUT, POST, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-Request-ID"
        )
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = "Origin"
    return response


@app.get("/health", tags=["system"])
def liveness() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "warehouse-os-api"})


# Compatibility-first routes are registered before retained contracts. They use
# the same URLs and response fields, but close the basic source/runtime/database
# chain and preserve exact diagnostics when one stage fails.
app.include_router(hosted_runtime_gateway_router)
app.include_router(workspace_v1_compat_router)
app.include_router(workspace_provision_compat_router)
app.include_router(hosting_session_extension_compat_router)
app.include_router(workspace_autonomy_router)
app.include_router(workspace_company_compat_router)
app.include_router(intelligent_hosting_compat_router)

# Native control planes are registered before the retained full-stack router so
# a compatibility route can never shadow a security-sensitive implementation.
app.include_router(shield_router)
app.include_router(browser_runtime_router)
app.include_router(database_browser_gateway_router)
app.include_router(confirmation_actions_router)
app.include_router(lighthouse_federation_router)
app.include_router(full_stack_router)
app.include_router(router)
app.include_router(compatibility_router)
app.include_router(digital_asset_router)
app.include_router(intelligent_hosting_router)
app.include_router(generic_data_router)
app.include_router(research_router)
app.include_router(task_collaboration_router)
app.include_router(cluster_status_router)
# Capability discovery remains complete, but executable readiness is derived
# only from concrete routes mounted up to this point.  The catch-all gateway
# below is a transport compatibility surface and must never activate a gene.
configure_native_capability_routes(app)
app.include_router(capability_gateway_router)


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
