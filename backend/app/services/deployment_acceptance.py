"""Manifest-driven private acceptance for staged workspace deployments."""

from __future__ import annotations

import json
import mimetypes
import re
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from uuid import UUID

import httpx
import psycopg
from fastapi import HTTPException
from psycopg import sql
from psycopg.rows import dict_row
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import tenant_session
from app.services import hosted_database
from app.services.digital_asset_hosting import WorkspaceCredential, _json_safe

_INTERNAL_URL = re.compile(r"^http://[a-zA-Z0-9_.-]+:[0-9]{1,5}$")
_MAX_RESPONSE_BYTES = 1024 * 1024


def ensure_candidate_runtime_running(
    credential: WorkspaceCredential,
    deployment_id: UUID,
    settings: Settings,
) -> None:
    """Wake a staged Runtime and wait for its controller health gate.

    Candidate validation can happen immediately after a build or after
    scale-to-zero has suspended the Runtime. Always requesting an idempotent
    wake also repairs the legacy state where an orphan reconciliation stopped
    the container while the database still said ``running``.
    """

    with tenant_session(credential.tenant_id) as session:
        state = session.execute(
            text(
                """
                UPDATE digital_asset.deployments
                SET runtime_state='wake_requested',
                    runtime_last_request_at=now(),
                    runtime_wake_requested_at=now(),
                    runtime_state_changed_at=now(),
                    runtime_wake_error=NULL
                WHERE id=:deployment_id AND workspace_id=:workspace_id
                  AND status='ready' AND health='healthy'
                RETURNING runtime_state
                """
            ),
            {
                "deployment_id": deployment_id,
                "workspace_id": credential.workspace_id,
            },
        ).scalar_one_or_none()
    if state is None:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "candidate_runtime_wake_failed",
                "message": "Only a healthy service Runtime can be woken for validation",
                "deployment_id": str(deployment_id),
                "route_changed": False,
                "retryable": False,
            },
        )

    deadline = time.monotonic() + max(1.0, float(settings.runtime_wake_timeout_seconds))
    observed_state = str(state)
    observed_error = ""
    while time.monotonic() < deadline:
        with tenant_session(credential.tenant_id) as session:
            observed = (
                session.execute(
                    text(
                        """
                        SELECT runtime_state,runtime_wake_error
                        FROM digital_asset.deployments
                        WHERE id=:deployment_id AND workspace_id=:workspace_id
                          AND status='ready' AND health='healthy'
                        """
                    ),
                    {
                        "deployment_id": deployment_id,
                        "workspace_id": credential.workspace_id,
                    },
                )
                .mappings()
                .one_or_none()
            )
        if observed is None:
            break
        observed_state = str(observed.get("runtime_state") or "unknown")
        observed_error = str(observed.get("runtime_wake_error") or "")
        if observed_state == "running":
            return
        if observed_state == "error":
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "candidate_runtime_wake_failed",
                    "message": observed_error or "Candidate Runtime failed its wake health gate",
                    "deployment_id": str(deployment_id),
                    "runtime_state": observed_state,
                    "route_changed": False,
                    "retryable": True,
                },
            )
        time.sleep(0.1)
    raise HTTPException(
        status_code=409,
        detail={
            "reason": "candidate_runtime_wake_timeout",
            "message": "Candidate Runtime did not become healthy before validation timed out",
            "deployment_id": str(deployment_id),
            "runtime_state": observed_state,
            "runtime_wake_error": observed_error or None,
            "route_changed": False,
            "retryable": True,
        },
    )


def _json_pointer(document: object, pointer: str) -> object:
    current = document
    if not pointer:
        return current
    for encoded in pointer.removeprefix("/").split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError) as exc:
                raise ValueError(f"JSON pointer segment is unavailable: {token}") from exc
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise ValueError(f"JSON pointer segment is unavailable: {token}")
    return current


def _http_acceptance(
    internal_url: str,
    probes: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[str]]:
    evidence: list[dict[str, object]] = []
    failures: list[str] = []
    with httpx.Client(timeout=15.0, follow_redirects=False) as client:
        for probe in probes:
            name = str(probe["name"])
            path = str(probe["path"])
            observed: dict[str, object] = {"name": name, "path": path}
            try:
                response = client.get(f"{internal_url}{path}")
                observed["status"] = response.status_code
                observed["content_type"] = response.headers.get("content-type", "")[:160]
                if len(response.content) > _MAX_RESPONSE_BYTES:
                    raise ValueError("response exceeds 1 MiB acceptance limit")
                expected_status = int(probe["expected_status"])
                if response.status_code != expected_status:
                    raise ValueError(
                        f"expected HTTP {expected_status}, observed {response.status_code}"
                    )
                operator = str(probe.get("operator") or "status_only")
                if operator != "status_only":
                    document = response.json()
                    value = _json_pointer(document, str(probe.get("json_pointer") or ""))
                    observed["value"] = value
                    expected = probe.get("expected")
                    if operator == "length_equals":
                        if not isinstance(value, (list, dict, str)) or len(value) != expected:
                            raise ValueError(
                                f"expected JSON length {expected}, observed "
                                + (
                                    str(len(value))
                                    if isinstance(value, (list, dict, str))
                                    else "non-sized"
                                )
                            )
                    elif value != expected:
                        raise ValueError(f"expected JSON value {expected!r}, observed {value!r}")
                observed["accepted"] = True
            except Exception as exc:
                observed["accepted"] = False
                observed["error"] = str(exc)[:500]
                failures.append(f"http:{name}")
            evidence.append(observed)
    return evidence, failures


def _static_candidate_root(result: dict[str, object], settings: Settings) -> Path:
    relative = str(result.get("runtime_rel_path") or "").strip()
    if not relative:
        raise ValueError("release_files_unavailable")
    data_root = settings.hosted_runtime_data_root.resolve()
    root = (data_root / relative).resolve()
    try:
        root.relative_to(data_root)
    except ValueError as exc:
        raise ValueError("unsafe_release_path") from exc
    if not (root / "index.html").is_file():
        raise ValueError("static_index_unavailable")
    return root


def _static_probe_target(root: Path, path: str) -> Path | None:
    decoded = unquote(urlsplit(path).path)
    relative = PurePosixPath(decoded.lstrip("/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe_static_probe_path")
    target = (root.joinpath(*relative.parts)).resolve() if relative.parts else root
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("unsafe_static_probe_path") from exc
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file() and not relative.suffix:
        target = root / "index.html"
    return target if target.is_file() else None


def _static_acceptance(
    root: Path,
    probes: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[str]]:
    effective_probes = probes or [
        {
            "name": "static-root",
            "path": "/",
            "expected_status": 200,
            "operator": "status_only",
        }
    ]
    evidence: list[dict[str, object]] = []
    failures: list[str] = []
    for probe in effective_probes:
        name = str(probe["name"])
        path = str(probe["path"])
        observed: dict[str, object] = {"name": name, "path": path}
        try:
            target = _static_probe_target(root, path)
            status = 200 if target is not None else 404
            observed["status"] = status
            observed["content_type"] = (
                mimetypes.guess_type(str(target))[0] if target is not None else ""
            ) or "application/octet-stream"
            expected_status = int(probe["expected_status"])
            if status != expected_status:
                raise ValueError(f"expected HTTP {expected_status}, observed {status}")
            operator = str(probe.get("operator") or "status_only")
            if operator != "status_only":
                if target is None:
                    raise ValueError("static response has no document")
                if target.stat().st_size > _MAX_RESPONSE_BYTES:
                    raise ValueError("response exceeds 1 MiB acceptance limit")
                document = json.loads(target.read_text(encoding="utf-8"))
                value = _json_pointer(document, str(probe.get("json_pointer") or ""))
                observed["value"] = value
                expected = probe.get("expected")
                if operator == "length_equals":
                    if not isinstance(value, (list, dict, str)) or len(value) != expected:
                        raise ValueError(
                            f"expected JSON length {expected}, observed "
                            + (
                                str(len(value))
                                if isinstance(value, (list, dict, str))
                                else "non-sized"
                            )
                        )
                elif value != expected:
                    raise ValueError(f"expected JSON value {expected!r}, observed {value!r}")
            observed["accepted"] = True
        except Exception as exc:
            observed["accepted"] = False
            observed["error"] = str(exc)[:500]
            failures.append(f"http:{name}")
        evidence.append(observed)
    return evidence, failures


def _database_acceptance(
    credential: WorkspaceCredential,
    settings: Settings,
    database_contract: dict[str, object],
) -> tuple[list[dict[str, object]], list[str]]:
    counts = database_contract.get("counts")
    assertions = counts if isinstance(counts, list) else []
    if not assertions:
        return [], []
    context = database_contract.get("context")
    context = context if isinstance(context, dict) else {}
    with tenant_session(credential.tenant_id) as session:
        database_url = hosted_database.runtime_database_url(
            session,
            credential.workspace_id,
            settings=settings,
        )
    if not database_url:
        return [], ["database:runtime_binding_unavailable"]
    evidence: list[dict[str, object]] = []
    failures: list[str] = []
    try:
        connection_context = psycopg.connect(
            database_url,
            row_factory=dict_row,
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
            application_name="warehouse-deployment-acceptance",
        )
        with connection_context as connection:
            connection.execute("SET LOCAL statement_timeout TO '15s'")
            connection.execute("SET LOCAL lock_timeout TO '3s'")
            for name, value in context.items():
                connection.execute(
                    "SELECT set_config(%s, %s, true)",
                    (str(name), str(value)),
                )
            for assertion in assertions:
                name = str(assertion["name"])
                filters = assertion.get("filters")
                filters = filters if isinstance(filters, dict) else {}
                where = sql.SQL("")
                parameters: list[object] = []
                if filters:
                    predicates = []
                    for column, value in filters.items():
                        if value is None:
                            predicates.append(sql.SQL("{} IS NULL").format(sql.Identifier(column)))
                        else:
                            predicates.append(sql.SQL("{} = %s").format(sql.Identifier(column)))
                            parameters.append(value)
                    where = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(predicates)
                statement = (
                    sql.SQL("SELECT count(*)::bigint AS value FROM {}.{}").format(
                        sql.Identifier(str(assertion["schema"])),
                        sql.Identifier(str(assertion["relation"])),
                    )
                    + where
                )
                observed: dict[str, object] = {
                    "name": name,
                    "relation": f"{assertion['schema']}.{assertion['relation']}",
                    "filters": filters,
                    "expected": int(assertion["expected"]),
                }
                try:
                    row = connection.execute(statement, parameters).fetchone()
                    value = int(row["value"])
                    observed["value"] = value
                    observed["accepted"] = value == int(assertion["expected"])
                    if not observed["accepted"]:
                        failures.append(f"database:{name}")
                except Exception as exc:
                    observed["accepted"] = False
                    observed["error"] = str(exc)[:500]
                    failures.append(f"database:{name}")
                evidence.append(observed)
    except Exception as exc:
        return evidence, [f"database:connection:{type(exc).__name__}"]
    return evidence, failures


def _lifecycle_evidence(
    rows: list[dict[str, object]],
    contract: dict[str, object],
) -> tuple[list[dict[str, object]], list[str]]:
    lifecycle = contract.get("lifecycle")
    lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
    jobs = lifecycle.get("jobs") if isinstance(lifecycle.get("jobs"), list) else []
    required = [
        job for job in jobs if isinstance(job, dict) and bool(job.get("required_before_activation"))
    ]
    evidence: list[dict[str, object]] = []
    failures: list[str] = []
    digest = str(contract.get("contract_digest") or "")
    for job in required:
        name = str(job.get("name"))
        matched = next(
            (
                row
                for row in rows
                if isinstance(row.get("requested_config"), dict)
                and isinstance(row["requested_config"].get("lifecycle_job"), dict)
                and row["requested_config"]["lifecycle_job"].get("name") == name
                and row["requested_config"]["lifecycle_job"].get("contract_digest") == digest
                and row.get("status") == "ready"
                and row.get("health") == "healthy"
            ),
            None,
        )
        accepted = matched is not None
        evidence.append(
            {
                "name": name,
                "accepted": accepted,
                "deployment_id": str(matched["id"]) if matched is not None else None,
            }
        )
        if not accepted:
            failures.append(f"lifecycle:{name}")
    return evidence, failures


def accept_workspace_deployment(
    credential: WorkspaceCredential,
    deployment_id: UUID | int,
    settings: Settings,
    *,
    ensure_runtime: bool = True,
) -> dict[str, object]:
    """Probe a candidate using its immutable source-declared compatibility contract."""

    credential.require("deploy:write")
    reference = str(deployment_id)
    with tenant_session(credential.tenant_id) as session:
        candidate = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.deployments
                    WHERE workspace_id=:workspace_id
                      AND (CAST(id AS text)=:reference OR CAST(legacy_id AS text)=:reference)
                    """
                ),
                {"workspace_id": credential.workspace_id, "reference": reference},
            )
            .mappings()
            .one_or_none()
        )
        if candidate is None:
            raise HTTPException(status_code=404, detail="Deployment not found")
        if candidate["status"] != "ready" or candidate["health"] != "healthy":
            raise HTTPException(
                status_code=409,
                detail="Only a healthy candidate can be accepted",
            )
        result = candidate.get("result") if isinstance(candidate.get("result"), dict) else {}
        if str(result.get("execution_mode") or "service") != "service":
            raise HTTPException(status_code=409, detail="A one-shot job cannot receive traffic")
        requested = (
            candidate.get("requested_config")
            if isinstance(candidate.get("requested_config"), dict)
            else {}
        )
        contract = (
            requested.get("compatibility_contract")
            if isinstance(requested.get("compatibility_contract"), dict)
            else None
        )
        if contract is None:
            health_path = str(result.get("health_path") or requested.get("health_path") or "/")
            contract = {
                "schema": "platform-detected",
                "contract_digest": str(candidate["request_digest"]),
                "lifecycle": {"jobs": []},
                "acceptance": {
                    "required_before_activation": False,
                    "http": [
                        {
                            "name": "health",
                            "path": health_path,
                            "expected_status": 200,
                            "operator": "status_only",
                        }
                    ],
                    "database": {"connection": "runtime", "context": {}, "counts": []},
                },
            }
        lifecycle_rows = [
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT id,status,health,requested_config
                    FROM digital_asset.deployments
                    WHERE workspace_id=:workspace_id AND source_version_id=:source_version_id
                      AND COALESCE(requested_config->>'execution_mode','service')='job'
                    ORDER BY completed_at DESC NULLS LAST,created_at DESC
                    """
                ),
                {
                    "workspace_id": credential.workspace_id,
                    "source_version_id": candidate["source_version_id"],
                },
            ).mappings()
        ]
        candidate_id = UUID(str(candidate["id"]))
        source_version_id = str(candidate["source_version_id"])
        internal_url = str(result.get("internal_url") or "").rstrip("/")

    acceptance = contract.get("acceptance")
    acceptance = acceptance if isinstance(acceptance, dict) else {}
    probes = acceptance.get("http") if isinstance(acceptance.get("http"), list) else []
    database_contract = (
        acceptance.get("database") if isinstance(acceptance.get("database"), dict) else {}
    )
    lifecycle, lifecycle_failures = _lifecycle_evidence(lifecycle_rows, contract)
    if str(result.get("runtime_kind") or "") == "static":
        try:
            static_root = _static_candidate_root(result, settings)
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "candidate_static_release_unavailable",
                    "message": str(exc),
                    "deployment_id": str(candidate_id),
                },
            ) from exc
        http_evidence, http_failures = _static_acceptance(static_root, probes)
        candidate_transport = "immutable_static_release"
    else:
        if not _INTERNAL_URL.fullmatch(internal_url):
            raise HTTPException(status_code=409, detail="Candidate internal URL is unavailable")
        if ensure_runtime:
            ensure_candidate_runtime_running(credential, candidate_id, settings)
        http_evidence, http_failures = _http_acceptance(internal_url, probes)
        candidate_transport = "private_runtime_network"
    database_evidence, database_failures = _database_acceptance(
        credential,
        settings,
        database_contract,
    )
    failures = [*lifecycle_failures, *http_failures, *database_failures]
    observed_at = datetime.now(UTC).isoformat()
    evidence = {
        "accepted": not failures,
        "observed_at": observed_at,
        "source_version_id": source_version_id,
        "contract_schema": contract.get("schema"),
        "contract_digest": contract.get("contract_digest"),
        "candidate_transport": candidate_transport,
        "lifecycle": lifecycle,
        "http": http_evidence,
        "database": database_evidence,
        "failures": failures,
    }
    with tenant_session(credential.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE digital_asset.deployments
                SET result=result || jsonb_build_object(
                  'acceptance',CAST(:acceptance AS jsonb),
                  'activation_deferred',CASE WHEN :accepted THEN false ELSE true END
                ),updated_at=now()
                WHERE id=:deployment_id AND workspace_id=:workspace_id
                """
            ),
            {
                "acceptance": json.dumps(evidence, ensure_ascii=False),
                "accepted": not failures,
                "deployment_id": candidate_id,
                "workspace_id": credential.workspace_id,
            },
        )
        sequence = int(
            session.execute(
                text(
                    "SELECT COALESCE(max(sequence),0)+1 FROM "
                    "digital_asset.deployment_events WHERE deployment_id=:id"
                ),
                {"id": candidate_id},
            ).scalar_one()
        )
        session.execute(
            text(
                """
                INSERT INTO digital_asset.deployment_events(
                  deployment_id,tenant_id,sequence,event_type,payload
                ) VALUES (
                  :id,:tenant_id,:sequence,:event_type,CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "id": candidate_id,
                "tenant_id": credential.tenant_id,
                "sequence": sequence,
                "event_type": "acceptance_succeeded" if not failures else "acceptance_rejected",
                "payload": json.dumps(
                    {
                        "credential_id": str(credential.credential_id),
                        "contract_digest": contract.get("contract_digest"),
                        "failures": failures,
                    }
                ),
            },
        )
    return {
        "ok": not failures,
        "accepted": not failures,
        "deployment_id": str(candidate_id),
        "evidence": _json_safe(evidence),
        "next_action": "activate_deployment" if not failures else "repair_and_restage",
    }
