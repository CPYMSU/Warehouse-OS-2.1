"""Executable, backward-compatible workspace hosting application contract."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath

from fastapi import HTTPException

LEGACY_HOSTING_SCHEMA = "warehouse.hosting-application.v2.2"
HOSTING_SCHEMA = "warehouse.hosting-application.v2.3"
SUPPORTED_HOSTING_SCHEMAS = frozenset({LEGACY_HOSTING_SCHEMA, HOSTING_SCHEMA})
MANIFEST_FILENAME = "warehouse.hosting.json"
MAX_MANIFEST_BYTES = 256 * 1024

_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,79}$")
_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_$]{0,62}$")
_JOB_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_GUC_NAME = re.compile(r"^[a-z][a-z0-9_.]{1,127}$")
_RUNTIME_TYPES = frozenset(
    {"static", "web", "api", "worker", "agent", "job", "container", "compose"}
)
_DATABASE_POLICIES = frozenset(
    {"platform_managed", "external", "workspace_managed", "none"}
)


def _invalid(field: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "reason": "hosting_manifest_invalid",
            "field": field,
            "message": message,
            "supported_schemas": sorted(SUPPORTED_HOSTING_SCHEMAS),
        },
    )


def _object(value: object, field: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise _invalid(field, "must be an object")
    return dict(value)


def _only(value: dict[str, object], allowed: set[str], field: str) -> None:
    extras = sorted(set(value) - allowed)
    if extras:
        raise _invalid(field, f"unsupported properties: {', '.join(extras)}")


def _bounded_string(
    value: object,
    field: str,
    *,
    required: bool = False,
    maximum: int = 8192,
) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _invalid(field, "must be a non-empty string")
    resolved = value.strip()
    if "\x00" in resolved or len(resolved) > maximum:
        raise _invalid(field, f"must contain at most {maximum} safe characters")
    return resolved


def _environment_name(value: object, field: str) -> str | None:
    resolved = _bounded_string(value, field, maximum=80)
    if resolved is not None and not _ENV_NAME.fullmatch(resolved):
        raise _invalid(field, "must be a safe environment variable name")
    return resolved


def _source_path(
    value: object,
    field: str,
    source_paths: set[str],
) -> str | None:
    resolved = _bounded_string(value, field, maximum=240)
    if resolved is None:
        return None
    path = PurePosixPath(resolved.replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise _invalid(field, "must be a safe source-relative path")
    normalized = path.as_posix()
    if source_paths and normalized.lower() not in source_paths:
        raise _invalid(field, "does not exist in the verified source archive")
    return normalized


def _http_path(value: object, field: str) -> str:
    resolved = _bounded_string(value, field, required=True, maximum=512)
    assert resolved is not None
    path = resolved.split("?", 1)[0]
    if not path.startswith("/") or "//" in path or ".." in PurePosixPath(path).parts:
        raise _invalid(field, "must be a safe absolute application path")
    return resolved


def _integer(
    value: object,
    field: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool):
        raise _invalid(field, "must be an integer")
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise _invalid(field, "must be an integer") from exc
    if resolved < minimum or resolved > maximum:
        raise _invalid(field, f"must be between {minimum} and {maximum}")
    return resolved


def _runtime_contract(
    value: object,
    source_paths: set[str],
) -> dict[str, object]:
    runtime = _object(value, "runtime")
    _only(
        runtime,
        {
            "type",
            "runtime",
            "runtime_profile",
            "entrypoint",
            "build_command",
            "start_command",
            "health_path",
            "port",
            "dockerfile",
            "compose_file",
            "route_service",
        },
        "runtime",
    )
    runtime_type = _bounded_string(runtime.get("type"), "runtime.type", required=True, maximum=20)
    if runtime_type not in _RUNTIME_TYPES:
        raise _invalid("runtime.type", "is not a supported Runtime type")
    normalized: dict[str, object] = {"type": runtime_type}
    for name in ("runtime", "runtime_profile"):
        if resolved := _bounded_string(runtime.get(name), f"runtime.{name}", maximum=120):
            normalized[name] = resolved
    for name in ("entrypoint", "dockerfile", "compose_file"):
        if resolved := _source_path(runtime.get(name), f"runtime.{name}", source_paths):
            normalized[name] = resolved
    for name in ("build_command", "start_command"):
        if resolved := _bounded_string(runtime.get(name), f"runtime.{name}"):
            normalized[name] = resolved
    if runtime_type not in {"worker", "agent", "job"}:
        normalized["health_path"] = _http_path(
            runtime.get("health_path") or "/healthz",
            "runtime.health_path",
        )
    elif runtime.get("health_path") is not None:
        normalized["health_path"] = _http_path(
            runtime["health_path"], "runtime.health_path"
        )
    if runtime.get("port") is not None:
        normalized["port"] = _integer(
            runtime["port"], "runtime.port", minimum=1, maximum=65535
        )
    if resolved := _bounded_string(
        runtime.get("route_service"), "runtime.route_service", maximum=120
    ):
        normalized["route_service"] = resolved
    return normalized


def _data_contract(value: object) -> dict[str, object]:
    data = _object(value, "data")
    _only(
        data,
        {
            "persistent_path",
            "database_url_env",
            "runtime_database_url_env",
            "migration_database_url_env",
            "database_policy",
        },
        "data",
    )
    persistent_path = data.get("persistent_path", "/workspace/data")
    if persistent_path != "/workspace/data":
        raise _invalid(
            "data.persistent_path",
            "the only persistent writable application path is /workspace/data",
        )
    normalized: dict[str, object] = {"persistent_path": "/workspace/data"}
    legacy_runtime_env = data.get("database_url_env")
    runtime_env = data.get("runtime_database_url_env", legacy_runtime_env)
    if legacy_runtime_env is not None and data.get("runtime_database_url_env") not in {
        None,
        legacy_runtime_env,
    }:
        raise _invalid(
            "data.runtime_database_url_env",
            "conflicts with legacy data.database_url_env",
        )
    if resolved := _environment_name(runtime_env, "data.runtime_database_url_env"):
        normalized["runtime_database_url_env"] = resolved
    if resolved := _environment_name(
        data.get("migration_database_url_env"), "data.migration_database_url_env"
    ):
        normalized["migration_database_url_env"] = resolved
    policy = str(data.get("database_policy") or "platform_managed").strip().lower()
    if policy not in _DATABASE_POLICIES:
        raise _invalid("data.database_policy", "is not a supported database policy")
    normalized["database_policy"] = policy
    return normalized


def _lifecycle_contract(
    value: object,
    data: dict[str, object],
    source_paths: set[str],
) -> dict[str, object]:
    lifecycle = _object(value, "lifecycle")
    _only(lifecycle, {"jobs"}, "lifecycle")
    raw_jobs = lifecycle.get("jobs", [])
    if not isinstance(raw_jobs, list) or len(raw_jobs) > 12:
        raise _invalid("lifecycle.jobs", "must be an array with at most 12 jobs")
    jobs: list[dict[str, object]] = []
    names: set[str] = set()
    for index, raw_job in enumerate(raw_jobs):
        field = f"lifecycle.jobs[{index}]"
        job = _object(raw_job, field)
        _only(
            job,
            {
                "name",
                "command",
                "runtime",
                "runtime_profile",
                "entrypoint",
                "build_command",
                "database_access",
                "database_url_env",
                "timeout_seconds",
                "required_before_activation",
            },
            field,
        )
        name = _bounded_string(job.get("name"), f"{field}.name", required=True, maximum=64)
        assert name is not None
        if not _JOB_NAME.fullmatch(name) or name in names:
            raise _invalid(f"{field}.name", "must be safe and unique")
        names.add(name)
        command = _bounded_string(
            job.get("command"), f"{field}.command", required=True, maximum=8192
        )
        access = str(job.get("database_access") or "none").strip().lower()
        if access not in {"none", "runtime", "migration"}:
            raise _invalid(
                f"{field}.database_access",
                "must be none, runtime, or migration",
            )
        env_name = _environment_name(job.get("database_url_env"), f"{field}.database_url_env")
        if access == "runtime" and not env_name:
            env_name = str(data.get("runtime_database_url_env") or "DATABASE_URL")
        if access == "migration" and not env_name:
            env_name = str(data.get("migration_database_url_env") or "MIGRATION_DATABASE_URL")
        normalized: dict[str, object] = {
            "name": name,
            "command": command,
            "database_access": access,
            "timeout_seconds": _integer(
                job.get("timeout_seconds", 1200),
                f"{field}.timeout_seconds",
                minimum=30,
                maximum=7200,
            ),
            "required_before_activation": bool(job.get("required_before_activation", False)),
        }
        if access != "none":
            normalized["database_url_env"] = env_name
        for key in ("runtime", "runtime_profile"):
            if resolved := _bounded_string(job.get(key), f"{field}.{key}", maximum=120):
                normalized[key] = resolved
        if resolved := _source_path(job.get("entrypoint"), f"{field}.entrypoint", source_paths):
            normalized["entrypoint"] = resolved
        if resolved := _bounded_string(job.get("build_command"), f"{field}.build_command"):
            normalized["build_command"] = resolved
        jobs.append(normalized)
    return {"jobs": jobs}


def _acceptance_contract(value: object) -> dict[str, object]:
    acceptance = _object(value, "acceptance")
    _only(acceptance, {"required_before_activation", "http", "database"}, "acceptance")
    raw_http = acceptance.get("http", [])
    if not isinstance(raw_http, list) or len(raw_http) > 20:
        raise _invalid("acceptance.http", "must be an array with at most 20 probes")
    http_probes: list[dict[str, object]] = []
    probe_names: set[str] = set()
    for index, raw_probe in enumerate(raw_http):
        field = f"acceptance.http[{index}]"
        probe = _object(raw_probe, field)
        _only(
            probe,
            {"name", "path", "expected_status", "json_pointer", "operator", "expected"},
            field,
        )
        name = _bounded_string(probe.get("name"), f"{field}.name", required=True, maximum=64)
        assert name is not None
        if not _JOB_NAME.fullmatch(name) or name in probe_names:
            raise _invalid(f"{field}.name", "must be safe and unique")
        probe_names.add(name)
        operator = str(probe.get("operator") or "status_only").strip().lower()
        if operator not in {"status_only", "equals", "length_equals"}:
            raise _invalid(f"{field}.operator", "is not supported")
        normalized_probe: dict[str, object] = {
            "name": name,
            "path": _http_path(probe.get("path"), f"{field}.path"),
            "expected_status": _integer(
                probe.get("expected_status", 200),
                f"{field}.expected_status",
                minimum=100,
                maximum=599,
            ),
            "operator": operator,
        }
        if operator != "status_only":
            pointer = probe.get("json_pointer", "")
            if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
                raise _invalid(f"{field}.json_pointer", "must be an RFC 6901 JSON pointer")
            if "expected" not in probe:
                raise _invalid(f"{field}.expected", "is required for this operator")
            if operator == "length_equals":
                normalized_probe["expected"] = _integer(
                    probe["expected"], f"{field}.expected", minimum=0, maximum=10_000_000
                )
            else:
                expected = probe["expected"]
                if not isinstance(expected, (str, int, float, bool)) and expected is not None:
                    raise _invalid(f"{field}.expected", "must be a JSON scalar")
                normalized_probe["expected"] = expected
            normalized_probe["json_pointer"] = pointer
        http_probes.append(normalized_probe)

    database = _object(acceptance.get("database"), "acceptance.database")
    _only(database, {"context", "counts"}, "acceptance.database")
    raw_context = _object(database.get("context"), "acceptance.database.context")
    context: dict[str, str] = {}
    for name, raw_value in raw_context.items():
        if not _GUC_NAME.fullmatch(str(name)):
            raise _invalid("acceptance.database.context", f"unsafe setting name: {name}")
        if not isinstance(raw_value, str) or len(raw_value) > 512 or "\x00" in raw_value:
            raise _invalid(f"acceptance.database.context.{name}", "must be a bounded string")
        context[str(name)] = raw_value
    raw_counts = database.get("counts", [])
    if not isinstance(raw_counts, list) or len(raw_counts) > 30:
        raise _invalid("acceptance.database.counts", "must contain at most 30 assertions")
    counts: list[dict[str, object]] = []
    count_names: set[str] = set()
    for index, raw_count in enumerate(raw_counts):
        field = f"acceptance.database.counts[{index}]"
        count = _object(raw_count, field)
        _only(count, {"name", "schema", "relation", "filters", "expected"}, field)
        name = _bounded_string(count.get("name"), f"{field}.name", required=True, maximum=64)
        assert name is not None
        if not _JOB_NAME.fullmatch(name) or name in count_names:
            raise _invalid(f"{field}.name", "must be safe and unique")
        count_names.add(name)
        schema = _bounded_string(count.get("schema"), f"{field}.schema", required=True, maximum=63)
        relation = _bounded_string(
            count.get("relation"), f"{field}.relation", required=True, maximum=63
        )
        assert schema is not None and relation is not None
        if not _IDENTIFIER.fullmatch(schema) or not _IDENTIFIER.fullmatch(relation):
            raise _invalid(field, "schema and relation must be safe PostgreSQL identifiers")
        raw_filters = _object(count.get("filters"), f"{field}.filters")
        filters: dict[str, object] = {}
        for column, filter_value in raw_filters.items():
            if not _IDENTIFIER.fullmatch(str(column)):
                raise _invalid(f"{field}.filters", f"unsafe column: {column}")
            if not isinstance(filter_value, (str, int, float, bool)) and filter_value is not None:
                raise _invalid(f"{field}.filters.{column}", "must be a JSON scalar")
            filters[str(column)] = filter_value
        counts.append(
            {
                "name": name,
                "schema": schema,
                "relation": relation,
                "filters": filters,
                "expected": _integer(
                    count.get("expected"), f"{field}.expected", minimum=0, maximum=2**63 - 1
                ),
            }
        )
    return {
        "required_before_activation": bool(
            acceptance.get("required_before_activation", bool(http_probes or counts))
        ),
        "http": http_probes,
        "database": {"connection": "runtime", "context": context, "counts": counts},
    }


def _deployment_contract(value: object, *, acceptance_required: bool) -> dict[str, object]:
    deployment = _object(value, "deployment")
    _only(
        deployment,
        {
            "activate_when_healthy",
            "strategy",
            "retain_previous",
            "require_acceptance_before_activation",
        },
        "deployment",
    )
    strategy = str(
        deployment.get("strategy") or ("staged" if acceptance_required else "automatic")
    ).strip().lower()
    if strategy not in {"automatic", "staged"}:
        raise _invalid("deployment.strategy", "must be automatic or staged")
    require_acceptance = bool(
        deployment.get("require_acceptance_before_activation", acceptance_required)
    )
    if acceptance_required and not require_acceptance:
        raise _invalid(
            "deployment.require_acceptance_before_activation",
            "cannot disable a declared required acceptance contract",
        )
    if require_acceptance:
        strategy = "staged"
    activate_default = bool(deployment.get("activate_when_healthy", not require_acceptance))
    return {
        "strategy": strategy,
        "activate_when_healthy": activate_default and not require_acceptance,
        "retain_previous": bool(deployment.get("retain_previous", True)),
        "require_acceptance_before_activation": require_acceptance,
    }


def validate_hosting_manifest(
    raw: object,
    *,
    source_paths: set[str] | None = None,
) -> dict[str, object]:
    """Validate and normalize a v2.2/v2.3 application manifest."""

    manifest = _object(raw, "manifest")
    _only(
        manifest,
        {"schema", "runtime", "data", "deployment", "lifecycle", "acceptance"},
        "manifest",
    )
    schema = _bounded_string(manifest.get("schema"), "schema", required=True, maximum=80)
    if schema not in SUPPORTED_HOSTING_SCHEMAS:
        raise _invalid("schema", "is not supported")
    if schema == LEGACY_HOSTING_SCHEMA and ({"lifecycle", "acceptance"} & set(manifest)):
        raise _invalid("schema", "lifecycle and acceptance require the v2.3 schema")
    paths = {str(path).lower() for path in (source_paths or set())}
    runtime = _runtime_contract(manifest.get("runtime"), paths)
    data = _data_contract(manifest.get("data"))
    lifecycle = _lifecycle_contract(manifest.get("lifecycle"), data, paths)
    acceptance = _acceptance_contract(manifest.get("acceptance"))
    deployment = _deployment_contract(
        manifest.get("deployment"),
        acceptance_required=bool(acceptance["required_before_activation"]),
    )
    normalized = {
        "schema": schema,
        "runtime": runtime,
        "data": data,
        "lifecycle": lifecycle,
        "acceptance": acceptance,
        "deployment": deployment,
    }
    digest = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**normalized, "contract_digest": digest}


def manifest_runtime_defaults(manifest: object) -> dict[str, object]:
    """Translate a validated manifest into the ordinary Runtime request shape."""

    if not isinstance(manifest, dict):
        return {}
    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    data = manifest.get("data") if isinstance(manifest.get("data"), dict) else {}
    deployment = (
        manifest.get("deployment") if isinstance(manifest.get("deployment"), dict) else {}
    )
    defaults = {
        "runtime_type": runtime.get("type"),
        "runtime": runtime.get("runtime"),
        "runtime_profile": runtime.get("runtime_profile"),
        "entrypoint": runtime.get("entrypoint"),
        "build_command": runtime.get("build_command"),
        "start_command": runtime.get("start_command"),
        "health_path": runtime.get("health_path"),
        "port": runtime.get("port"),
        "dockerfile": runtime.get("dockerfile"),
        "compose_file": runtime.get("compose_file"),
        "route_service": runtime.get("route_service"),
        "database_url_env": data.get("runtime_database_url_env"),
        "activate": deployment.get("activate_when_healthy"),
        "compatibility_contract": manifest,
    }
    return {key: value for key, value in defaults.items() if value not in (None, "")}


def declared_lifecycle_job(manifest: object, name: str) -> dict[str, object] | None:
    if not isinstance(manifest, dict):
        return None
    lifecycle = manifest.get("lifecycle")
    lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
    jobs = lifecycle.get("jobs") if isinstance(lifecycle.get("jobs"), list) else []
    return next(
        (dict(job) for job in jobs if isinstance(job, dict) and job.get("name") == name),
        None,
    )
