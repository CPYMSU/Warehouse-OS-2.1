"""Versioned, secret-free contract for portable Warehouse Pages applications."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath

from fastapi import HTTPException

PAGES_APP_SCHEMA = "warehouse.pages-application.v1"
PAGES_APP_MANIFEST_FILENAME = "warehouse.pages.json"
MAX_PAGES_APP_MANIFEST_BYTES = 256 * 1024

_COLLECTION_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_FUNCTION_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,62}$")
_SECRET_REF_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
_CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,79}$")
_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
_ACCESS_RULES = frozenset({"deny", "session", "owner"})


def _invalid(field: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "reason": "pages_app_manifest_invalid",
            "field": field,
            "message": message,
        },
    )


def _object(
    value: object,
    field: str,
    *,
    allowed: frozenset[str],
    required: frozenset[str] = frozenset(),
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _invalid(field, "must be an object")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise _invalid(field, f"contains unsupported fields: {', '.join(unknown)}")
    missing = sorted(required - set(value))
    if missing:
        raise _invalid(field, f"is missing required fields: {', '.join(missing)}")
    return dict(value)


def _string(
    value: object,
    field: str,
    *,
    minimum: int = 1,
    maximum: int = 200,
) -> str:
    if not isinstance(value, str):
        raise _invalid(field, "must be a string")
    rendered = value.strip()
    if not minimum <= len(rendered) <= maximum:
        raise _invalid(field, f"must contain {minimum}-{maximum} characters")
    return rendered


def _boolean(value: object, field: str, *, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise _invalid(field, "must be a boolean")
    return value


def _path(value: object, field: str, *, allow_dot: bool = False) -> str:
    rendered = _string(value, field, maximum=300).replace("\\", "/").strip("/")
    if allow_dot and rendered in {"", "."}:
        return "."
    parsed = PurePosixPath(rendered)
    if (
        not rendered
        or parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in parsed.parts)
    ):
        raise _invalid(field, "must be a safe relative package path")
    return parsed.as_posix()


def _declared_file(root: str, entry: str) -> str:
    return entry if root == "." else f"{root}/{entry}"


def _require_file(paths: set[str] | None, path: str, field: str) -> None:
    if paths is not None and path.lower() not in paths:
        raise _invalid(field, f"declared file is not present in the source package: {path}")


def _require_tree(paths: set[str] | None, path: str, field: str) -> None:
    if paths is None or path == ".":
        return
    prefix = path.lower().rstrip("/") + "/"
    if not any(item.startswith(prefix) for item in paths):
        raise _invalid(field, f"declared source tree is not present in the package: {path}")


def _access(value: object, field: str) -> dict[str, str]:
    payload = _object(
        value,
        field,
        allowed=frozenset({"read", "write"}),
        required=frozenset({"read", "write"}),
    )
    output: dict[str, str] = {}
    for operation in ("read", "write"):
        rule = _string(payload[operation], f"{field}.{operation}", maximum=20).lower()
        if rule not in _ACCESS_RULES:
            raise _invalid(
                f"{field}.{operation}",
                "must be deny, session or owner",
            )
        output[operation] = rule
    return output


def _canonical_digest(value: dict[str, object]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_pages_app_manifest(
    raw: object,
    *,
    source_paths: set[str] | None = None,
    generated: bool = False,
) -> dict[str, object]:
    """Validate and normalize one portable Pages application manifest."""

    paths = {str(item).lower() for item in source_paths} if source_paths is not None else None
    manifest = _object(
        raw,
        "manifest",
        allowed=frozenset(
            {"schema", "name", "version", "web", "data", "functions", "device", "design"}
        ),
        required=frozenset({"schema", "web"}),
    )
    if manifest.get("schema") != PAGES_APP_SCHEMA:
        raise _invalid("schema", f"must equal {PAGES_APP_SCHEMA}")

    web = _object(
        manifest["web"],
        "web",
        allowed=frozenset({"root", "entry", "compute", "navigation_fallback", "service_worker"}),
        required=frozenset({"root", "entry"}),
    )
    web_root = _path(web["root"], "web.root", allow_dot=True)
    web_entry = _path(web["entry"], "web.entry")
    entry_path = _declared_file(web_root, web_entry)
    _require_file(paths, entry_path, "web.entry")
    compute = str(web.get("compute") or "browser").strip().lower()
    if compute != "browser":
        raise _invalid("web.compute", "Pages v1 compute must be browser")
    navigation_fallback = str(web.get("navigation_fallback") or "index").strip().lower()
    if navigation_fallback not in {"index", "404"}:
        raise _invalid("web.navigation_fallback", "must be index or 404")
    normalized_web: dict[str, object] = {
        "root": web_root,
        "entry": web_entry,
        "compute": "browser",
        "navigation_fallback": navigation_fallback,
    }
    if web.get("service_worker") not in (None, ""):
        service_worker = _path(web["service_worker"], "web.service_worker")
        _require_file(
            paths,
            _declared_file(web_root, service_worker),
            "web.service_worker",
        )
        normalized_web["service_worker"] = service_worker

    data = _object(
        manifest.get("data") or {},
        "data",
        allowed=frozenset({"mode", "default_access", "collections", "sync"}),
    )
    data_mode = str(data.get("mode") or "none").strip().lower()
    if data_mode not in {"none", "platform_api"}:
        raise _invalid("data.mode", "must be none or platform_api")
    default_access = _access(
        data.get("default_access") or {"read": "deny", "write": "deny"},
        "data.default_access",
    )
    collections_value = data.get("collections") or []
    if not isinstance(collections_value, list) or len(collections_value) > 128:
        raise _invalid("data.collections", "must be an array with at most 128 items")
    collections: list[dict[str, object]] = []
    collection_names: set[str] = set()
    for index, value in enumerate(collections_value):
        field = f"data.collections[{index}]"
        item = _object(
            value,
            field,
            allowed=frozenset({"name", "access", "offline"}),
            required=frozenset({"name"}),
        )
        name = _string(item["name"], f"{field}.name", maximum=63).lower()
        if not _COLLECTION_RE.fullmatch(name) or name in collection_names:
            raise _invalid(f"{field}.name", "must be a unique safe collection name")
        collection_names.add(name)
        collections.append(
            {
                "name": name,
                "access": _access(
                    item.get("access") or {"read": "deny", "write": "deny"},
                    f"{field}.access",
                ),
                "offline": _boolean(
                    item.get("offline"),
                    f"{field}.offline",
                    default=True,
                ),
            }
        )
    sync = _object(
        data.get("sync") or {},
        "data.sync",
        allowed=frozenset({"mode", "offline_store", "cursor_field", "pull_limit"}),
    )
    sync_mode = str(sync.get("mode") or "none").strip().lower()
    if sync_mode not in {"none", "cursor"}:
        raise _invalid("data.sync.mode", "must be none or cursor")
    offline_store = str(sync.get("offline_store") or "indexeddb").strip().lower()
    if offline_store not in {"indexeddb", "none"}:
        raise _invalid("data.sync.offline_store", "must be indexeddb or none")
    cursor_field = str(sync.get("cursor_field") or "updated_at").strip()
    if not _COLLECTION_RE.fullmatch(cursor_field):
        raise _invalid("data.sync.cursor_field", "must be a safe field name")
    pull_limit = sync.get("pull_limit", 500)
    if (
        isinstance(pull_limit, bool)
        or not isinstance(pull_limit, int)
        or not 1 <= pull_limit <= 5000
    ):
        raise _invalid("data.sync.pull_limit", "must be an integer between 1 and 5000")
    if data_mode == "none" and (collections or sync_mode != "none"):
        raise _invalid("data.mode", "must be platform_api when collections or sync are declared")
    if default_access != {"read": "deny", "write": "deny"}:
        raise _invalid(
            "data.default_access",
            "must remain deny/deny; grant access only on named collections",
        )
    normalized_data = {
        "mode": data_mode,
        "default_access": default_access,
        "collections": sorted(collections, key=lambda item: str(item["name"])),
        "sync": {
            "mode": sync_mode,
            "offline_store": offline_store,
            "cursor_field": cursor_field,
            "pull_limit": pull_limit,
        },
    }

    functions_value = manifest.get("functions") or []
    if not isinstance(functions_value, list) or len(functions_value) > 64:
        raise _invalid("functions", "must be an array with at most 64 items")
    functions: list[dict[str, object]] = []
    function_names: set[str] = set()
    function_routes: set[str] = set()
    for index, value in enumerate(functions_value):
        field = f"functions[{index}]"
        item = _object(
            value,
            field,
            allowed=frozenset(
                {
                    "name",
                    "route",
                    "methods",
                    "runtime",
                    "source",
                    "handler",
                    "auth",
                    "secret_refs",
                    "timeout_seconds",
                }
            ),
            required=frozenset({"name", "route", "runtime"}),
        )
        name = _string(item["name"], f"{field}.name", maximum=63).lower()
        if not _FUNCTION_RE.fullmatch(name) or name in function_names:
            raise _invalid(f"{field}.name", "must be a unique safe function name")
        function_names.add(name)
        route = _string(item["route"], f"{field}.route", maximum=200)
        if not route.startswith("/api/") or ".." in PurePosixPath(route).parts:
            raise _invalid(f"{field}.route", "must be a safe /api/ route")
        if route in function_routes:
            raise _invalid(f"{field}.route", "must be unique")
        function_routes.add(route)
        methods_value = item.get("methods") or ["POST"]
        if not isinstance(methods_value, list) or not 1 <= len(methods_value) <= 5:
            raise _invalid(f"{field}.methods", "must contain 1-5 HTTP methods")
        methods = sorted(
            {_string(method, f"{field}.methods", maximum=10).upper() for method in methods_value}
        )
        if any(method not in _HTTP_METHODS for method in methods):
            raise _invalid(f"{field}.methods", "contains an unsupported HTTP method")
        runtime = _string(item["runtime"], f"{field}.runtime", maximum=40).lower()
        if runtime not in {"serverless_node", "serverless_python", "database_function"}:
            raise _invalid(
                f"{field}.runtime",
                "must be serverless_node, serverless_python or database_function",
            )
        source = None
        if runtime != "database_function":
            source = _path(item.get("source"), f"{field}.source")
            _require_tree(paths, source, f"{field}.source")
        handler = None
        if item.get("handler") not in (None, ""):
            handler = _string(item["handler"], f"{field}.handler", maximum=200)
        auth = str(item.get("auth") or "session").strip().lower()
        if auth not in {"session", "owner", "workspace"}:
            raise _invalid(f"{field}.auth", "must be session, owner or workspace")
        secret_refs_value = item.get("secret_refs") or []
        if not isinstance(secret_refs_value, list) or len(secret_refs_value) > 32:
            raise _invalid(f"{field}.secret_refs", "must contain at most 32 secret names")
        secret_refs = sorted(
            {_string(secret, f"{field}.secret_refs", maximum=128) for secret in secret_refs_value}
        )
        if any(not _SECRET_REF_RE.fullmatch(secret) for secret in secret_refs):
            raise _invalid(
                f"{field}.secret_refs",
                "must contain environment-style secret references, never values",
            )
        timeout = item.get("timeout_seconds", 30)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 60:
            raise _invalid(f"{field}.timeout_seconds", "must be an integer between 1 and 60")
        normalized: dict[str, object] = {
            "name": name,
            "route": route,
            "methods": methods,
            "runtime": runtime,
            "auth": auth,
            "secret_refs": secret_refs,
            "timeout_seconds": timeout,
        }
        if source is not None:
            normalized["source"] = source
        if handler is not None:
            normalized["handler"] = handler
        functions.append(normalized)

    device = _object(
        manifest.get("device") or {},
        "device",
        allowed=frozenset({"mode", "capabilities"}),
    )
    device_mode = str(device.get("mode") or "disabled").strip().lower()
    if device_mode not in {"disabled", "optional"}:
        raise _invalid("device.mode", "must be disabled or optional")
    capabilities_value = device.get("capabilities") or []
    if not isinstance(capabilities_value, list) or len(capabilities_value) > 32:
        raise _invalid("device.capabilities", "must contain at most 32 capability names")
    capabilities = sorted(
        {_string(value, "device.capabilities", maximum=80).lower() for value in capabilities_value}
    )
    if any(not _CAPABILITY_RE.fullmatch(value) for value in capabilities):
        raise _invalid("device.capabilities", "contains an unsafe capability name")
    if device_mode == "disabled" and capabilities:
        raise _invalid("device.capabilities", "requires device.mode=optional")

    design = _object(
        manifest.get("design") or {},
        "design",
        allowed=frozenset({"roots", "api_schema", "components"}),
    )
    roots_value = design.get("roots") or []
    if not isinstance(roots_value, list) or len(roots_value) > 16:
        raise _invalid("design.roots", "must contain at most 16 paths")
    design_roots = sorted({_path(value, "design.roots", allow_dot=True) for value in roots_value})
    for root in design_roots:
        _require_tree(paths, root, "design.roots")
    normalized_design: dict[str, object] = {"roots": design_roots}
    for key in ("api_schema", "components"):
        if design.get(key) in (None, ""):
            continue
        declared = _path(design[key], f"design.{key}")
        _require_file(paths, declared, f"design.{key}")
        normalized_design[key] = declared

    normalized_manifest: dict[str, object] = {
        "schema": PAGES_APP_SCHEMA,
        "name": _string(manifest.get("name") or "Warehouse Pages application", "name", maximum=120),
        "version": _string(manifest.get("version") or "1.0.0", "version", maximum=80),
        "web": normalized_web,
        "data": normalized_data,
        "functions": sorted(functions, key=lambda item: str(item["name"])),
        "device": {"mode": device_mode, "capabilities": capabilities},
        "design": normalized_design,
    }
    digest = _canonical_digest(normalized_manifest)
    return {
        **normalized_manifest,
        "contract_digest": digest,
        "generated": bool(generated),
        "secrets_embedded": False,
        "database_reconcile": "background_control_plane",
    }


def synthesize_pages_app_manifest(
    source_paths: set[str],
    *,
    name: str,
    version: str = "1.0.0",
) -> dict[str, object]:
    """Produce a conservative compatibility contract for a legacy source package."""

    normalized_paths = {str(item).replace("\\", "/").strip("/") for item in source_paths}
    lowered = {item.lower(): item for item in normalized_paths}
    selected_root = None
    for root in ("frontend", "site", "dist", "build", "public", "."):
        candidate = "index.html" if root == "." else f"{root}/index.html"
        if candidate in lowered:
            selected_root = root
            break
    if selected_root is None:
        raise _invalid(
            "web.entry",
            "cannot synthesize a Pages package because no supported index.html was found",
        )
    service_worker = "sw.js" if selected_root == "." else f"{selected_root}/sw.js"
    web: dict[str, object] = {
        "root": selected_root,
        "entry": "index.html",
        "compute": "browser",
        "navigation_fallback": "index",
    }
    if service_worker in lowered:
        web["service_worker"] = "sw.js"
    design_roots = [
        root for root in ("design", "docs") if any(path.startswith(root + "/") for path in lowered)
    ]
    return validate_pages_app_manifest(
        {
            "schema": PAGES_APP_SCHEMA,
            "name": name,
            "version": version,
            "web": web,
            "data": {
                "mode": "none",
                "default_access": {"read": "deny", "write": "deny"},
                "collections": [],
                "sync": {"mode": "none", "offline_store": "indexeddb"},
            },
            "functions": [],
            "device": {"mode": "disabled", "capabilities": []},
            "design": {"roots": design_roots},
        },
        source_paths=normalized_paths,
        generated=True,
    )


def portable_pages_app_manifest(manifest: dict[str, object]) -> dict[str, object]:
    """Strip platform observations and retain only the authorable package contract."""

    return {
        key: manifest[key]
        for key in ("schema", "name", "version", "web", "data", "functions", "device", "design")
        if key in manifest
    }
