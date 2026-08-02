"""Durable, version-pinned research computation services."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.db.session import tenant_session
from app.services.object_storage import LocalContentAddressedObjectStore
from app.services.research_vault import (
    _audit,
    _project_row,
    _require_read,
    _require_write,
    _uuid,
    add_file_version,
)

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings


TERMINAL_STATUSES = frozenset({"succeeded", "failed", "cancelled", "timed_out"})
RUNTIMES = (
    {
        "key": "python-3.13",
        "label": "Python 3.13 Scientific",
        "entrypoint_extensions": [".py"],
        "packages": ["numpy", "pandas", "scipy"],
        "network": "disabled",
    },
)
MAX_INPUT_FILES = 128
MAX_INPUT_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARGUMENTS = 32


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (UUID, datetime, date, Decimal)):
        return str(value)
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(
        _json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _safe_path(value: object, *, label: str) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if (
        not raw
        or raw.startswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
        or len(raw) > 500
    ):
        raise HTTPException(status_code=422, detail=f"{label} must be a safe relative path")
    return str(path)


def _execution_root(settings: Settings) -> Path:
    root = settings.research_execution_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("Research execution root is unsafe")
    return root


def _job_root(settings: Settings, job_id: UUID) -> Path:
    root = _execution_root(settings)
    candidate = (root / "jobs" / str(job_id)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unsafe execution path") from exc
    return candidate


def execution_runtimes(actor: ActorContext) -> dict[str, object]:
    _require_read(actor)
    return {
        "source": "research_executor_contract",
        "runtimes": list(RUNTIMES),
        "isolation": {
            "network": "disabled",
            "root_filesystem": "read_only",
            "process_user": "unique_per_job",
            "shell": "disabled",
            "inputs": "immutable_file_versions",
            "outputs": "sha256_verified",
        },
    }


def _input_rows(session, project_id: UUID, requested: object) -> list[dict[str, object]]:
    identifiers: list[UUID] = []
    if requested is not None:
        if not isinstance(requested, list) or not requested:
            raise HTTPException(
                status_code=422,
                detail="input_file_version_ids must be a non-empty array when provided",
            )
        if len(requested) > MAX_INPUT_FILES:
            raise HTTPException(status_code=422, detail="Too many input file versions")
        for value in requested:
            identifier = _uuid(value)
            if identifier is None:
                raise HTTPException(status_code=422, detail="Invalid input file version id")
            if identifier not in identifiers:
                identifiers.append(identifier)

    if identifiers:
        rows = (
            session.execute(
                text(
                    """
                    SELECT v.*, f.logical_path
                    FROM research.file_versions v
                    JOIN research.files f ON f.id = v.file_id
                    WHERE v.project_id = :project_id AND v.id = ANY(:ids)
                    ORDER BY f.logical_path
                    """
                ),
                {"project_id": project_id, "ids": identifiers},
            )
            .mappings()
            .all()
        )
        if len(rows) != len(identifiers):
            raise HTTPException(status_code=404, detail="One or more input versions not found")
    else:
        rows = (
            session.execute(
                text(
                    """
                    SELECT DISTINCT ON (f.id) v.*, f.logical_path
                    FROM research.files f
                    JOIN research.file_versions v ON v.file_id = f.id
                    WHERE f.project_id = :project_id AND f.status = 'active'
                    ORDER BY f.id, v.version DESC
                    """
                ),
                {"project_id": project_id},
            )
            .mappings()
            .all()
        )
    if not rows:
        raise HTTPException(status_code=422, detail="The project has no executable file versions")
    if len(rows) > MAX_INPUT_FILES:
        raise HTTPException(status_code=422, detail="Too many input file versions")
    if sum(int(row["size_bytes"]) for row in rows) > MAX_INPUT_BYTES:
        raise HTTPException(status_code=422, detail="Execution inputs exceed 2 GiB")
    return [dict(row) for row in rows]


def _resource_limits(payload: dict[str, object], settings: Settings) -> dict[str, int]:
    supplied = payload.get("resource_limits")
    values = supplied if isinstance(supplied, dict) else {}
    try:
        timeout_seconds = int(
            values.get("timeout_seconds") or settings.research_execution_timeout_seconds
        )
        memory_mb = int(values.get("memory_mb") or 1024)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid execution resource limits") from exc
    if not 5 <= timeout_seconds <= 900:
        raise HTTPException(status_code=422, detail="timeout_seconds must be between 5 and 900")
    if not 128 <= memory_mb <= 2048:
        raise HTTPException(status_code=422, detail="memory_mb must be between 128 and 2048")
    return {
        "timeout_seconds": timeout_seconds,
        "memory_mb": memory_mb,
        "cpu_seconds": min(timeout_seconds, 600),
        "max_processes": 32,
        "max_output_bytes": min(settings.research_execution_max_output_bytes, 100 * 1024 * 1024),
        "max_artifacts": 100,
    }


def _arguments(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_ARGUMENTS:
        raise HTTPException(
            status_code=422, detail=f"arguments must contain at most {MAX_ARGUMENTS} items"
        )
    result = [str(item) for item in value]
    if any(len(item) > 4096 or "\x00" in item for item in result):
        raise HTTPException(status_code=422, detail="Invalid execution argument")
    return result


def _materialize_inputs(
    settings: Settings,
    actor: ActorContext,
    job_id: UUID,
    inputs: list[dict[str, object]],
    manifest: dict[str, object],
) -> None:
    store = LocalContentAddressedObjectStore(settings.asset_storage_root)
    job_root = _job_root(settings, job_id)
    input_root = job_root / "inputs"
    output_root = job_root / "outputs"
    job_root.mkdir(parents=True, exist_ok=False, mode=0o700)
    input_root.mkdir(mode=0o700)
    output_root.mkdir(mode=0o700)
    try:
        for item in inputs:
            relative = _safe_path(item["logical_path"], label="logical_path")
            source = store.path_for(str(item["object_key"]))
            target = (input_root / relative).resolve()
            target.relative_to(input_root.resolve())
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            digest = hashlib.sha256()
            with source.open("rb") as reader, target.open("xb") as writer:
                while chunk := reader.read(1024 * 1024):
                    digest.update(chunk)
                    writer.write(chunk)
            if digest.hexdigest() != str(item["content_sha256"]):
                raise HTTPException(status_code=409, detail=f"Input checksum mismatch: {relative}")
            target.chmod(0o400)
        manifest_path = job_root / "manifest.json"
        manifest_path.write_bytes(_canonical(manifest) + b"\n")
        manifest_path.chmod(0o400)
    except Exception:
        shutil.rmtree(job_root, ignore_errors=True)
        raise


def create_execution(
    actor: ActorContext,
    project_ref: object,
    payload: dict[str, object],
    settings: Settings,
    *,
    parent_job_id: UUID | None = None,
) -> dict[str, object]:
    _require_write(actor)
    runtime = str(payload.get("runtime") or "python-3.13")
    if runtime != "python-3.13":
        raise HTTPException(status_code=422, detail="Unsupported research runtime")
    entrypoint = _safe_path(payload.get("entrypoint"), label="entrypoint")
    if Path(entrypoint).suffix.lower() != ".py":
        raise HTTPException(status_code=422, detail="python-3.13 requires a .py entrypoint")
    arguments = _arguments(payload.get("arguments"))
    limits = _resource_limits(payload, settings)
    job_id = uuid4()
    job_code = f"EXE-{job_id.hex[:10].upper()}"

    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        inputs = _input_rows(session, project["id"], payload.get("input_file_version_ids"))
        run_id = _uuid(payload.get("run_id"))
        if payload.get("run_id") and run_id is None:
            raise HTTPException(status_code=422, detail="Invalid run_id")
        if run_id is not None:
            exists = session.execute(
                text("SELECT 1 FROM research.runs WHERE project_id = :project_id AND id = :id"),
                {"project_id": project["id"], "id": run_id},
            ).scalar_one_or_none()
            if not exists:
                raise HTTPException(status_code=404, detail="Research run not found")

    if entrypoint not in {str(item["logical_path"]) for item in inputs}:
        raise HTTPException(
            status_code=422,
            detail="entrypoint must identify one of the pinned input file versions",
        )
    input_manifest = {
        "schema": "warehouse-research-execution/v1",
        "job_id": str(job_id),
        "project_id": str(project["id"]),
        "runtime": runtime,
        "entrypoint": entrypoint,
        "arguments": arguments,
        "resource_limits": limits,
        "total_input_bytes": sum(int(item["size_bytes"]) for item in inputs),
        "inputs": [
            {
                "file_version_id": str(item["id"]),
                "logical_path": str(item["logical_path"]),
                "version": int(item["version"]),
                "content_type": str(item["content_type"]),
                "content_sha256": str(item["content_sha256"]),
                "size_bytes": int(item["size_bytes"]),
                "git_sha": str(item["git_sha"] or ""),
            }
            for item in inputs
        ],
    }
    manifest_sha256 = _digest(input_manifest)
    _materialize_inputs(settings, actor, job_id, inputs, input_manifest)
    title = str(payload.get("title") or f"Execute {entrypoint}").strip()
    if not title:
        title = f"Execute {entrypoint}"
    try:
        with tenant_session(actor.tenant_id) as session:
            row = (
                session.execute(
                    text(
                        """
                        INSERT INTO research.execution_jobs(
                          id, tenant_id, project_id, run_id, parent_job_id,
                          job_code, title, runtime, entrypoint, arguments,
                          input_manifest, manifest_sha256, resource_limits, requested_by
                        ) VALUES (
                          :id, :tenant_id, :project_id, :run_id, :parent_job_id,
                          :job_code, :title, :runtime, :entrypoint, CAST(:arguments AS jsonb),
                          CAST(:manifest AS jsonb), :manifest_sha256,
                          CAST(:limits AS jsonb), :requested_by
                        ) RETURNING *
                        """
                    ),
                    {
                        "id": job_id,
                        "tenant_id": actor.tenant_id,
                        "project_id": project["id"],
                        "run_id": run_id,
                        "parent_job_id": parent_job_id,
                        "job_code": job_code,
                        "title": title[:300],
                        "runtime": runtime,
                        "entrypoint": entrypoint,
                        "arguments": json.dumps(arguments, ensure_ascii=False),
                        "manifest": json.dumps(input_manifest, ensure_ascii=False),
                        "manifest_sha256": manifest_sha256,
                        "limits": json.dumps(limits),
                        "requested_by": actor.user_id,
                    },
                )
                .mappings()
                .one()
            )
            session.execute(
                text(
                    """
                    INSERT INTO research.execution_events(
                      tenant_id, project_id, job_id, event_type, message, payload
                    ) VALUES (
                      :tenant_id, :project_id, :job_id, 'queued',
                      'Execution package verified and queued', CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "job_id": job_id,
                    "payload": json.dumps({"manifest_sha256": manifest_sha256}),
                },
            )
            _audit(
                session,
                actor,
                "research.execution.queued",
                {
                    "project_id": project["id"],
                    "job_id": job_id,
                    "job_code": job_code,
                    "manifest_sha256": manifest_sha256,
                },
            )
    except Exception:
        shutil.rmtree(_job_root(settings, job_id), ignore_errors=True)
        raise
    return {"ok": True, "execution": _json_safe(dict(row))}


def list_executions(actor: ActorContext, project_ref: object) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        rows = (
            session.execute(
                text(
                    """
                    SELECT j.*,
                           (SELECT count(*) FROM research.execution_artifacts a
                            WHERE a.job_id = j.id)::integer AS artifact_count
                    FROM research.execution_jobs j
                    WHERE j.project_id = :project_id
                    ORDER BY j.created_at DESC LIMIT 100
                    """
                ),
                {"project_id": project["id"]},
            )
            .mappings()
            .all()
        )
    return {
        "source": "research_execution_queue",
        "project": _json_safe(project),
        "executions": [_json_safe(dict(row)) for row in rows],
    }


def execution_detail(
    actor: ActorContext, project_ref: object, execution_ref: object
) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        identifier = _uuid(execution_ref)
        clause = "id = :value" if identifier else "job_code = :value"
        job = (
            session.execute(
                text(
                    f"SELECT * FROM research.execution_jobs "
                    f"WHERE project_id = :project_id AND {clause}"
                ),
                {"project_id": project["id"], "value": identifier or str(execution_ref)},
            )
            .mappings()
            .one_or_none()
        )
        if job is None:
            raise HTTPException(status_code=404, detail="Research execution not found")
        events = (
            session.execute(
                text("SELECT * FROM research.execution_events WHERE job_id = :id ORDER BY id"),
                {"id": job["id"]},
            )
            .mappings()
            .all()
        )
        artifacts = (
            session.execute(
                text(
                    "SELECT * FROM research.execution_artifacts "
                    "WHERE job_id = :id ORDER BY relative_path"
                ),
                {"id": job["id"]},
            )
            .mappings()
            .all()
        )
    return {
        "source": "research_execution_queue",
        "project": _json_safe(project),
        "execution": _json_safe(dict(job)),
        "events": [_json_safe(dict(row)) for row in events],
        "artifacts": [_json_safe(dict(row)) for row in artifacts],
    }


def cancel_execution(
    actor: ActorContext, project_ref: object, execution_ref: object
) -> dict[str, object]:
    _require_write(actor)
    detail = execution_detail(actor, project_ref, execution_ref)
    job = detail["execution"]
    if str(job["status"]) in TERMINAL_STATUSES:
        return {"ok": True, "execution": job, "already_terminal": True}
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    UPDATE research.execution_jobs
                    SET cancel_requested_at = now(),
                        status = CASE WHEN status IN ('queued', 'preparing')
                                      THEN 'cancelled' ELSE status END,
                        finished_at = CASE WHEN status IN ('queued', 'preparing')
                                           THEN now() ELSE finished_at END
                    WHERE id = :id RETURNING *
                    """
                ),
                {"id": _uuid(job["id"])},
            )
            .mappings()
            .one()
        )
        session.execute(
            text(
                """
                INSERT INTO research.execution_events(
                  tenant_id, project_id, job_id, event_type, message
                ) VALUES (:tenant_id, :project_id, :job_id, 'cancel_requested',
                          'Cancellation requested by researcher')
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "project_id": _uuid(job["project_id"]),
                "job_id": _uuid(job["id"]),
            },
        )
        _audit(
            session,
            actor,
            "research.execution.cancel_requested",
            {"project_id": job["project_id"], "job_id": job["id"]},
        )
    return {"ok": True, "execution": _json_safe(dict(row))}


def retry_execution(
    actor: ActorContext,
    project_ref: object,
    execution_ref: object,
    settings: Settings,
) -> dict[str, object]:
    detail = execution_detail(actor, project_ref, execution_ref)
    job = detail["execution"]
    manifest = job.get("input_manifest") if isinstance(job, dict) else None
    inputs = manifest.get("inputs") if isinstance(manifest, dict) else None
    payload = {
        "title": f"Retry {job['job_code']}",
        "runtime": job["runtime"],
        "entrypoint": job["entrypoint"],
        "arguments": job["arguments"],
        "run_id": job.get("run_id"),
        "resource_limits": job["resource_limits"],
        "input_file_version_ids": [item["file_version_id"] for item in inputs or []],
    }
    return create_execution(
        actor,
        project_ref,
        payload,
        settings,
        parent_job_id=_uuid(job["id"]),
    )


def artifact_descriptor(
    actor: ActorContext,
    project_ref: object,
    execution_ref: object,
    artifact_ref: object,
    settings: Settings,
) -> dict[str, object]:
    _require_read(actor)
    detail = execution_detail(actor, project_ref, execution_ref)
    job = detail["execution"]
    artifact_id = _uuid(artifact_ref)
    artifact = next(
        (item for item in detail["artifacts"] if _uuid(item["id"]) == artifact_id), None
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Execution artifact not found")
    output_root = (_job_root(settings, _uuid(job["id"])) / "outputs").resolve()
    path = (output_root / _safe_path(artifact["relative_path"], label="artifact path")).resolve()
    try:
        path.relative_to(output_root)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unsafe artifact path") from exc
    if not path.is_file() or path.is_symlink():
        raise HTTPException(status_code=410, detail="Execution artifact is unavailable")
    return {**artifact, "path": path, "job": job}


def promote_artifact(
    actor: ActorContext,
    project_ref: object,
    execution_ref: object,
    artifact_ref: object,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    _require_write(actor)
    descriptor = artifact_descriptor(actor, project_ref, execution_ref, artifact_ref, settings)
    artifact_id = _uuid(descriptor["id"])
    logical_path = _safe_path(
        payload.get("logical_path")
        or f"results/{descriptor['job']['job_code']}/{descriptor['relative_path']}",
        label="logical_path",
    )
    store = LocalContentAddressedObjectStore(settings.asset_storage_root)
    with descriptor["path"].open("rb") as stream:
        stored = store.put_stream(
            tenant_id=actor.tenant_id,
            stream=stream,
            max_bytes=settings.research_execution_max_output_bytes,
            expected_sha256=str(descriptor["content_sha256"]),
        )
    result = add_file_version(
        actor,
        project_ref,
        stored=stored,
        store=store,
        original_filename=Path(str(descriptor["relative_path"])).name,
        content_type=str(descriptor["content_type"]),
        logical_path=logical_path,
        commit_message=str(
            payload.get("commit_message") or f"Promote {descriptor['job']['job_code']} artifact"
        ),
        settings=settings,
    )
    version = result["version"]
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                "UPDATE research.execution_artifacts "
                "SET promoted_file_version_id = :version_id WHERE id = :id"
            ),
            {"version_id": _uuid(version["id"]), "id": artifact_id},
        )
        _audit(
            session,
            actor,
            "research.execution.artifact_promoted",
            {
                "job_id": descriptor["job"]["id"],
                "artifact_id": descriptor["id"],
                "file_version_id": version["id"],
                "logical_path": logical_path,
            },
        )
    return {"ok": True, "artifact": _json_safe(descriptor), **result}
