"""Compatibility-first public gateway for hosted workspace applications.

The permanent workspace entry is a real application boundary: browser cookies,
Authorization headers, redirects, request IDs and root-relative frontend assets
must continue to work under ``/assets/{tenant}/{workspace}/``.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse

from app.api import digital_assets as legacy
from app.core.config import Settings, get_settings
from app.services.workspace_deployments import active_workspace_runtime

router = APIRouter(tags=["hosted-runtime-gateway"])

_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "proxy-connection",
    }
)
_REQUEST_EXCLUDED = _HOP_BY_HOP | {"host", "content-length"}
_RESPONSE_EXCLUDED = _HOP_BY_HOP | {
    "content-length",
    "content-encoding",
    "server",
    "date",
}


def _prefix(tenant_slug: str, workspace_key: str) -> str:
    return f"/assets/{tenant_slug}/{workspace_key}"


def _browser_compatibility_script(prefix: str) -> str:
    encoded = prefix.replace("\\", "\\\\").replace("'", "\\'")
    return f"""<script>(function(){{
const P='{encoded}';
const map=(u)=>{{if(typeof u!=='string'||!u.startsWith('/')||u.startsWith(P+'/'))return u;
if(u.startsWith('//'))return u;return P+u;}};
const originalFetch=window.fetch;if(originalFetch)window.fetch=function(input,init){{
if(typeof input==='string')input=map(input);else if(input&&input.url&&input.url.startsWith('/'))input=new Request(map(input.url),input);
return originalFetch.call(this,input,init);}};
if(window.XMLHttpRequest){{const open=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u){{
arguments[1]=map(u);return open.apply(this,arguments);}};}}
if(window.EventSource){{const Native=window.EventSource;window.EventSource=function(u,c){{return new Native(map(u),c);}};window.EventSource.prototype=Native.prototype;}}
if(window.WebSocket){{const Native=window.WebSocket;window.WebSocket=function(u,p){{
if(typeof u==='string'&&u.startsWith('/')){{const scheme=location.protocol==='https:'?'wss:':'ws:';u=scheme+'//'+location.host+map(u);}}
return p===undefined?new Native(u):new Native(u,p);}};window.WebSocket.prototype=Native.prototype;}}
for(const method of ['pushState','replaceState']){{const original=history[method];history[method]=function(s,t,u){{
if(typeof u==='string')u=map(u);return original.call(this,s,t,u);}};}}
window.__WAREHOUSE_WORKSPACE_PREFIX__=P;
}})();</script>"""


def _rewrite_text(content: bytes, content_type: str, prefix: str) -> bytes:
    lowered = content_type.lower()
    if not any(token in lowered for token in ("text/html", "text/css", "application/xhtml")):
        return content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    escaped_prefix = prefix.rstrip("/")
    if "text/html" in lowered or "application/xhtml" in lowered:
        pattern = re.compile(
            r"(?P<attr>\b(?:src|href|action|poster)\s*=\s*)(?P<quote>['\"])/(?P<path>(?!/)[^'\"]*)",
            re.IGNORECASE,
        )
        text = pattern.sub(
            lambda match: (
                match.group("attr")
                + match.group("quote")
                + escaped_prefix
                + "/"
                + match.group("path")
            ),
            text,
        )
        script = _browser_compatibility_script(escaped_prefix)
        if re.search(r"<head(?:\s[^>]*)?>", text, re.IGNORECASE):
            text = re.sub(
                r"(<head(?:\s[^>]*)?>)",
                lambda match: match.group(1) + script,
                text,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            text = script + text
    text = re.sub(
        r"url\(\s*(['\"]?)/(?!/)",
        lambda match: f"url({match.group(1)}{escaped_prefix}/",
        text,
        flags=re.IGNORECASE,
    )
    if "text/css" in lowered:
        text = re.sub(
            r"(@import\s+['\"])/(?!/)",
            lambda match: match.group(1) + escaped_prefix + "/",
            text,
            flags=re.IGNORECASE,
        )
    return text.encode("utf-8")


def _rewrite_location(location: str, internal_url: str, prefix: str) -> str:
    clean_prefix = prefix.rstrip("/")
    if location.startswith(internal_url):
        suffix = location.removeprefix(internal_url)
        return clean_prefix + (suffix if suffix.startswith("/") else "/" + suffix)
    parsed = urlsplit(location)
    if not parsed.scheme and location.startswith("/") and not location.startswith(clean_prefix + "/"):
        return clean_prefix + location
    return location


def _rewrite_cookie(cookie: str, prefix: str) -> str:
    clean_prefix = prefix.rstrip("/") + "/"
    if re.search(r"(?i);\s*path=/($|;)", cookie):
        return re.sub(
            r"(?i)(;\s*path=)/(?=$|;)",
            lambda match: match.group(1) + clean_prefix,
            cookie,
        )
    if not re.search(r"(?i);\s*path=", cookie):
        return cookie + f"; Path={clean_prefix}"
    return cookie


def _static_response(route: dict[str, object], runtime_path: str, settings: Settings) -> Response:
    root = (settings.hosted_runtime_data_root / str(route["runtime_rel_path"])).resolve()
    try:
        root.relative_to(settings.hosted_runtime_data_root.resolve())
    except ValueError:
        raise HTTPException(status_code=503, detail="Runtime route is unsafe") from None
    target = (root / runtime_path).resolve() if runtime_path else root / "index.html"
    try:
        target.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=404, detail="Hosted file not found") from None
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file() and not Path(runtime_path).suffix:
        target = root / "index.html"
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Hosted file not found")
    media_type = legacy.mimetypes.guess_type(str(target))[0] if hasattr(legacy, "mimetypes") else None
    content_type = media_type or "application/octet-stream"
    if content_type in {"text/html", "text/css"}:
        content = _rewrite_text(target.read_bytes(), content_type, "")
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "X-Warehouse-Deployment": str(route["deployment_id"]),
                "X-Content-Type-Options": "nosniff",
            },
        )
    return FileResponse(
        target,
        headers={
            "X-Warehouse-Deployment": str(route["deployment_id"]),
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _proxy_response(
    route: dict[str, object],
    runtime_path: str,
    request: Request,
    tenant_slug: str,
    workspace_key: str,
) -> Response:
    upstreams = [
        str(value).rstrip("/")
        for value in (route.get("internal_urls") or [route.get("internal_url")])
        if value
    ]
    if not upstreams:
        raise HTTPException(status_code=502, detail="Hosted Runtime has no active upstream")
    prefix = _prefix(tenant_slug, workspace_key)
    suffix = "/" + runtime_path.lstrip("/")
    if request.url.query:
        suffix += "?" + request.url.query
    headers: list[tuple[str, str]] = []
    for key, value in request.headers.multi_items():
        if key.lower() not in _REQUEST_EXCLUDED:
            headers.append((key, value))
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = request.client.host if request.client else ""
    headers.extend(
        [
            ("x-forwarded-prefix", prefix),
            ("x-forwarded-host", request.headers.get("host", "")),
            ("x-forwarded-proto", request.url.scheme),
            ("x-forwarded-for", ", ".join(value for value in (forwarded_for, client_ip) if value)),
            ("x-request-id", request.headers.get("x-request-id", "")),
        ]
    )
    body = await request.body()
    upstream = None
    selected = upstreams[0]
    last_error: Exception | None = None
    timeout = httpx.Timeout(connect=10, read=120, write=120, pool=10)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        for internal_url in upstreams:
            try:
                upstream = await client.request(
                    request.method,
                    internal_url + suffix,
                    headers=headers,
                    content=body,
                )
                selected = internal_url
                break
            except httpx.HTTPError as exc:
                last_error = exc
    if upstream is None:
        raise HTTPException(
            status_code=502,
            detail={
                "reason": "hosted_runtime_unavailable",
                "message": "Every active Runtime upstream was unreachable",
                "stage": "route.proxy",
                "component": "public_route",
                "retryable": True,
                "next_action": "inspect deployment health and Runtime logs",
            },
        ) from last_error
    content_type = upstream.headers.get("content-type", "application/octet-stream")
    content = _rewrite_text(upstream.content, content_type, prefix)
    response = Response(content=content, status_code=upstream.status_code)
    for key, value in upstream.headers.multi_items():
        lowered = key.lower()
        if lowered in _RESPONSE_EXCLUDED or lowered == "set-cookie":
            continue
        if lowered == "location":
            value = _rewrite_location(value, selected, prefix)
        response.headers.append(key, value)
    for cookie in upstream.headers.get_list("set-cookie"):
        response.headers.append("set-cookie", _rewrite_cookie(cookie, prefix))
    response.headers["X-Warehouse-Deployment"] = str(route["deployment_id"])
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


async def runtime_response(
    tenant_slug: str,
    workspace_key: str,
    runtime_path: str,
    request: Request,
    settings: Settings,
) -> Response | None:
    route = active_workspace_runtime(tenant_slug, workspace_key)
    if route is None:
        return None
    prefix = _prefix(tenant_slug, workspace_key)
    if route["kind"] == "static":
        root = (settings.hosted_runtime_data_root / str(route["runtime_rel_path"])).resolve()
        try:
            root.relative_to(settings.hosted_runtime_data_root.resolve())
        except ValueError:
            raise HTTPException(status_code=503, detail="Runtime route is unsafe") from None
        target = (root / runtime_path).resolve() if runtime_path else root / "index.html"
        try:
            target.relative_to(root)
        except ValueError:
            raise HTTPException(status_code=404, detail="Hosted file not found") from None
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file() and not Path(runtime_path).suffix:
            target = root / "index.html"
        if not target.is_file():
            raise HTTPException(status_code=404, detail="Hosted file not found")
        content_type = legacy.guess_type(str(target))[0] if hasattr(legacy, "guess_type") else ""
        content_type = content_type or "application/octet-stream"
        content = _rewrite_text(target.read_bytes(), content_type, prefix)
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "X-Warehouse-Deployment": str(route["deployment_id"]),
                "X-Content-Type-Options": "nosniff",
            },
        )
    return await _proxy_response(route, runtime_path, request, tenant_slug, workspace_key)


@router.api_route(
    "/assets/{tenant_slug}/{workspace_key}/",
    methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
async def hosted_workspace_entry(
    tenant_slug: str,
    workspace_key: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    response = await runtime_response(
        tenant_slug, workspace_key, "", request, settings
    )
    if response is not None:
        return response
    return await legacy.hosted_workspace_entry(
        tenant_slug, workspace_key, request, settings
    )


@router.api_route(
    "/assets/{tenant_slug}/{workspace_key}/{runtime_path:path}",
    methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
async def hosted_workspace_runtime_path(
    tenant_slug: str,
    workspace_key: str,
    runtime_path: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    response = await runtime_response(
        tenant_slug, workspace_key, runtime_path, request, settings
    )
    if response is None:
        raise HTTPException(
            status_code=404,
            detail={
                "reason": "hosted_runtime_not_active",
                "stage": "route.resolve",
                "component": "public_route",
                "retryable": True,
                "next_action": "observe the latest deployment and repair its failed stage",
            },
        )
    return response
