"""Warehouse OS Pages shell and compatibility gateway for hosted applications.

The canonical entry is ``/apps/{site_key}/``. It embeds an isolated runtime
origin while the compatibility route keeps cookies, redirects, request IDs and
root-relative frontend assets working under ``/assets/{tenant}/{workspace}/``.
"""

from __future__ import annotations

import hashlib
import re
from html import escape
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.api import digital_assets as legacy
from app.core.config import Settings, get_settings
from app.services.pages_runtime import (
    pages_entry_path,
    pages_url,
    resolve_pages_site_key,
)
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


def _public_prefix(request: Request, tenant_slug: str, workspace_key: str) -> str:
    if getattr(request.state, "pages_hostname_route", None):
        return ""
    return _prefix(tenant_slug, workspace_key)


def _static_cache_headers(
    route: dict[str, object], runtime_path: str, content_type: str
) -> dict[str, str]:
    release = str(route.get("release_digest") or route["deployment_id"])
    identity = hashlib.sha256(f"{release}:{runtime_path or 'index.html'}".encode()).hexdigest()
    filename = Path(runtime_path or "index.html").name.lower()
    lowered_type = content_type.lower()
    if "text/html" in lowered_type or filename in {"service-worker.js", "sw.js"}:
        cache_control = "public, max-age=0, s-maxage=30, must-revalidate"
    elif re.search(r"(?:^|[.-])[a-f0-9]{8,}(?:[.-]|$)", filename):
        cache_control = "public, max-age=31536000, immutable"
    else:
        cache_control = "public, max-age=300, s-maxage=600, stale-while-revalidate=60"
    return {
        "Cache-Control": cache_control,
        "ETag": f'"{identity}"',
        "X-Warehouse-Release": release,
    }


def _browser_compatibility_script(prefix: str) -> str:
    encoded = prefix.replace("\\", "\\\\").replace("'", "\\'")
    return f"""<script>(function(){{
const P='{encoded}';
const map=(u)=>{{if(typeof u!=='string'||!u.startsWith('/')||u.startsWith(P+'/'))return u;
if(u.startsWith('//'))return u;return P+u;}};
const originalFetch=window.fetch;if(originalFetch)window.fetch=function(input,init){{
if(typeof input==='string')input=map(input);else if(input&&input.url&&input.url.startsWith('/'))input=new Request(map(input.url),input);
return originalFetch.call(this,input,init);}};
if(window.XMLHttpRequest){{const open=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u){{arguments[1]=map(u);return open.apply(this,arguments);}};}}
if(window.EventSource){{const Native=window.EventSource;window.EventSource=function(u,c){{return new Native(map(u),c);}};window.EventSource.prototype=Native.prototype;}}
if(window.WebSocket){{const Native=window.WebSocket;window.WebSocket=function(u,p){{if(typeof u==='string'&&u.startsWith('/')){{const scheme=location.protocol==='https:'?'wss:':'ws:';u=scheme+'//'+location.host+map(u);}}return p===undefined?new Native(u):new Native(u,p);}};window.WebSocket.prototype=Native.prototype;}}
for(const method of ['pushState','replaceState']){{const original=history[method];history[method]=function(s,t,u){{if(typeof u==='string')u=map(u);return original.call(this,s,t,u);}};}}
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
    clean_prefix = prefix.rstrip("/")
    if "text/html" in lowered or "application/xhtml" in lowered:
        pattern = re.compile(
            r"(?P<attr>\b(?:src|href|action|poster)\s*=\s*)(?P<quote>['\"])/(?P<path>(?!/)[^'\"]*)",
            re.IGNORECASE,
        )
        text = pattern.sub(
            lambda match: (
                match.group("attr")
                + match.group("quote")
                + clean_prefix
                + "/"
                + match.group("path")
            ),
            text,
        )
        script = _browser_compatibility_script(clean_prefix)
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
        lambda match: f"url({match.group(1)}{clean_prefix}/",
        text,
        flags=re.IGNORECASE,
    )
    if "text/css" in lowered:
        text = re.sub(
            r"(@import\s+['\"])/(?!/)",
            lambda match: match.group(1) + clean_prefix + "/",
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
    if not parsed.scheme and location.startswith("/") and not location.startswith(
        clean_prefix + "/"
    ):
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


def _pages_shell_document(
    *,
    site_key: str,
    runtime_path: str,
    query: str,
    settings: Settings,
) -> tuple[str, str]:
    encoded_path = quote(
        str(runtime_path or "").lstrip("/"), safe="/-._~!$&'()*+,;=:@"
    )
    frame_url = pages_url(site_key, settings) + "/" + encoded_path
    if query:
        frame_url += "?" + query
    safe_frame_url = escape(frame_url, quote=True)
    safe_site_key = escape(site_key)
    document = f"""<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="robots" content="index,follow">
  <title>{safe_site_key} · Warehouse OS</title>
  <style>
    html,body,iframe{{width:100%;height:100%;margin:0;border:0;background:#fff}}
    body{{overflow:hidden}}
    iframe{{display:block}}
  </style>
</head>
<body>
  <iframe
    src="{safe_frame_url}"
    title="{safe_site_key}"
    sandbox="allow-downloads allow-forms allow-modals allow-popups allow-presentation allow-same-origin allow-scripts"
    referrerpolicy="strict-origin-when-cross-origin"
    allow="clipboard-read; clipboard-write; fullscreen; geolocation; microphone; camera"
  ></iframe>
</body>
</html>"""
    return document, frame_url


def _pages_shell_response(
    site_key: str,
    runtime_path: str,
    request: Request,
    settings: Settings,
) -> Response:
    route = resolve_pages_site_key(site_key)
    if route is None:
        return JSONResponse(
            status_code=404,
            content={
                "detail": {
                    "reason": "pages_site_not_found",
                    "site_key": site_key,
                }
            },
            headers={"Cache-Control": "no-store"},
        )
    document, frame_url = _pages_shell_document(
        site_key=str(route["site_key"]),
        runtime_path=runtime_path,
        query=request.url.query,
        settings=settings,
    )
    frame_origin = pages_url(str(route["site_key"]), settings)
    return HTMLResponse(
        document,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'none'; "
                "style-src 'unsafe-inline'; "
                f"frame-src {frame_origin}; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Warehouse-Pages-Site": str(route["site_key"]),
            "X-Warehouse-Pages-Frame": frame_url,
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
    prefix = _public_prefix(request, tenant_slug, workspace_key)
    suffix = "/" + runtime_path.lstrip("/")
    if request.url.query:
        suffix += "?" + request.url.query
    headers = [
        (key, value)
        for key, value in request.headers.items()
        if key.lower() not in _REQUEST_EXCLUDED
    ]
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = request.client.host if request.client else ""
    headers.extend(
        [
            ("x-forwarded-prefix", prefix or "/"),
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
    prefix = _public_prefix(request, tenant_slug, workspace_key)
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
        content_type = guess_type(str(target))[0] or "application/octet-stream"
        headers = {
            **_static_cache_headers(route, runtime_path, content_type),
            "X-Warehouse-Deployment": str(route["deployment_id"]),
            "X-Content-Type-Options": "nosniff",
        }
        if request.headers.get("if-none-match") == headers["ETag"]:
            return Response(status_code=304, headers=headers)
        raw_content = target.read_bytes()
        content = raw_content if not prefix else _rewrite_text(raw_content, content_type, prefix)
        return Response(
            content=content,
            media_type=content_type,
            headers=headers,
        )
    return await _proxy_response(route, runtime_path, request, tenant_slug, workspace_key)


@router.api_route(
    "/apps/{site_key}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def warehouse_pages_entry_redirect(
    site_key: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    route = resolve_pages_site_key(site_key)
    if route is None:
        return JSONResponse(
            status_code=404,
            content={
                "detail": {
                    "reason": "pages_site_not_found",
                    "site_key": site_key,
                }
            },
            headers={"Cache-Control": "no-store"},
        )
    target = pages_entry_path(str(route["site_key"]))
    if request.url.query:
        target += "?" + request.url.query
    return RedirectResponse(target, status_code=308)


@router.api_route(
    "/apps/{site_key}/",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def warehouse_pages_entry(
    site_key: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    return _pages_shell_response(site_key, "", request, settings)


@router.api_route(
    "/apps/{site_key}/{runtime_path:path}",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def warehouse_pages_runtime_path(
    site_key: str,
    runtime_path: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    return _pages_shell_response(site_key, runtime_path, request, settings)


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
    response = await runtime_response(tenant_slug, workspace_key, "", request, settings)
    if response is not None:
        return response
    return await legacy.hosted_workspace_entry(tenant_slug, workspace_key, request, settings)


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
