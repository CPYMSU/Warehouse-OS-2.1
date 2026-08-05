"""Evidence-led research planning, execution, review and release services."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import tenant_session
from app.services.research_vault import (
    _audit,
    _project_row,
    _require_read,
    _require_write,
    _uuid,
)

if TYPE_CHECKING:
    from app.api.deps import ActorContext


DMP_FIELDS = (
    "research_question",
    "hypothesis",
    "data_collection",
    "ethics_legal_security",
    "storage_preservation",
    "sharing_reuse",
    "responsibilities",
)
PROTOCOL_STATUSES = frozenset({"draft", "locked", "retired"})
RUN_STATUSES = frozenset({"planned", "running", "completed", "failed", "cancelled"})
CLAIM_STATUSES = frozenset(
    {"draft", "submitted", "accepted", "changes_requested", "rejected"}
)
EVIDENCE_RELATIONS = frozenset({"supports", "contradicts", "method", "context"})
REVIEW_TARGETS = {
    "dmp": ("research.dmp_revisions", "id"),
    "protocol": ("research.protocols", "id"),
    "claim": ("research.claims", "id"),
    "release": ("research.releases", "id"),
}
REVIEW_DECISIONS = frozenset({"comment", "approve", "changes_requested", "reject"})


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (UUID, datetime, date, Decimal)):
        return str(value)
    return value


def _canonical(value: object) -> str:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_review(actor: ActorContext) -> None:
    if "research.review" in actor.permissions:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Research review permission denied",
    )


def require_research_review(actor: ActorContext) -> None:
    """Public permission guard for review and release routes."""

    _require_review(actor)


def _payload_dict(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _row_by_id(
    session: Session,
    table: str,
    project_id: UUID,
    value: object,
    *,
    label: str,
    lock: bool = False,
) -> dict[str, object]:
    identifier = _uuid(value)
    if identifier is None:
        raise HTTPException(status_code=422, detail=f"Invalid {label} id")
    suffix = " FOR UPDATE" if lock else ""
    row = (
        session.execute(
            text(
                f"SELECT * FROM {table} "
                f"WHERE project_id = :project_id AND id = :id{suffix}"
            ),
            {"project_id": project_id, "id": identifier},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return dict(row)


def _workflow_rows(
    session: Session, project_id: UUID
) -> dict[str, list[dict[str, object]]]:
    queries = {
        "dmp_history": """
            SELECT d.*, u.display_name AS author_name
            FROM research.dmp_revisions d
            LEFT JOIN iam.users u ON u.id = d.created_by
            WHERE d.project_id = :project_id
            ORDER BY d.version DESC
        """,
        "protocols": """
            SELECT p.*, u.display_name AS author_name
            FROM research.protocols p
            LEFT JOIN iam.users u ON u.id = p.created_by
            WHERE p.project_id = :project_id
            ORDER BY p.created_at DESC
        """,
        "runs": """
            SELECT r.*, p.protocol_code, p.title AS protocol_title,
                   u.display_name AS author_name
            FROM research.runs r
            LEFT JOIN research.protocols p ON p.id = r.protocol_id
            LEFT JOIN iam.users u ON u.id = r.created_by
            WHERE r.project_id = :project_id
            ORDER BY r.created_at DESC
        """,
        "claims": """
            SELECT c.*, u.display_name AS author_name
            FROM research.claims c
            LEFT JOIN iam.users u ON u.id = c.created_by
            WHERE c.project_id = :project_id
            ORDER BY c.created_at DESC
        """,
        "evidence": """
            SELECT e.*, f.logical_path, v.version AS file_version,
                   v.content_sha256, v.git_sha, r.run_code, r.title AS run_title
            FROM research.claim_evidence e
            LEFT JOIN research.file_versions v ON v.id = e.file_version_id
            LEFT JOIN research.files f ON f.id = v.file_id
            LEFT JOIN research.runs r ON r.id = e.run_id
            WHERE e.project_id = :project_id
            ORDER BY e.created_at DESC
        """,
        "reviews": """
            SELECT r.*, u.display_name AS reviewer_name
            FROM research.reviews r
            LEFT JOIN iam.users u ON u.id = r.reviewer_id
            WHERE r.project_id = :project_id
            ORDER BY r.created_at DESC
        """,
        "reproduction_checks": """
            SELECT c.*, u.display_name AS executor_name
            FROM research.reproduction_checks c
            LEFT JOIN iam.users u ON u.id = c.executed_by
            WHERE c.project_id = :project_id
            ORDER BY c.executed_at DESC
        """,
        "executions": """
            SELECT j.*,
                   (SELECT count(*) FROM research.execution_artifacts a
                    WHERE a.job_id = j.id)::integer AS artifact_count
            FROM research.execution_jobs j
            WHERE j.project_id = :project_id
            ORDER BY j.created_at DESC
            LIMIT 100
        """,
        "releases": """
            SELECT r.*, u.display_name AS releaser_name
            FROM research.releases r
            LEFT JOIN iam.users u ON u.id = r.released_by
            WHERE r.project_id = :project_id
            ORDER BY r.version DESC
        """,
    }
    result: dict[str, list[dict[str, object]]] = {}
    for key, query in queries.items():
        rows = (
            session.execute(text(query), {"project_id": project_id})
            .mappings()
            .all()
        )
        result[key] = [_json_safe(dict(row)) for row in rows]  # type: ignore[list-item]
    return result


def workflow_detail(actor: ActorContext, project_ref: object) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        rows = _workflow_rows(session, project["id"])
    evidence_by_claim: dict[str, list[dict[str, object]]] = {}
    for item in rows["evidence"]:
        evidence_by_claim.setdefault(str(item["claim_id"]), []).append(item)
    reviews_by_target: dict[str, list[dict[str, object]]] = {}
    for item in rows["reviews"]:
        reviews_by_target.setdefault(
            f"{item['target_type']}:{item['target_id']}", []
        ).append(item)
    for claim in rows["claims"]:
        claim["evidence"] = evidence_by_claim.get(str(claim["id"]), [])
        claim["reviews"] = reviews_by_target.get(f"claim:{claim['id']}", [])
    for protocol in rows["protocols"]:
        protocol["reviews"] = reviews_by_target.get(
            f"protocol:{protocol['id']}", []
        )
    current_dmp = rows["dmp_history"][0] if rows["dmp_history"] else None
    if current_dmp:
        current_dmp["reviews"] = reviews_by_target.get(
            f"dmp:{current_dmp['id']}", []
        )
    stats = {
        "dmp_version": int(current_dmp["version"]) if current_dmp else 0,
        "protocols": len(rows["protocols"]),
        "locked_protocols": sum(
            1 for item in rows["protocols"] if item["status"] == "locked"
        ),
        "runs": len(rows["runs"]),
        "completed_runs": sum(
            1 for item in rows["runs"] if item["status"] == "completed"
        ),
        "claims": len(rows["claims"]),
        "accepted_claims": sum(
            1 for item in rows["claims"] if item["status"] == "accepted"
        ),
        "evidence_links": len(rows["evidence"]),
        "reviews": len(rows["reviews"]),
        "reproduction_status": (
            rows["reproduction_checks"][0]["status"]
            if rows["reproduction_checks"]
            else "not_checked"
        ),
        "executions": len(rows["executions"]),
        "successful_executions": sum(
            1 for item in rows["executions"] if item["status"] == "succeeded"
        ),
        "running_executions": sum(
            1
            for item in rows["executions"]
            if item["status"] in {"queued", "preparing", "running"}
        ),
        "releases": len(rows["releases"]),
    }
    return {
        "source": "research_operating_model",
        "project": _json_safe(project),
        "dmp": current_dmp,
        **rows,
        "stats": stats,
        "workflow": [
            "plan",
            "govern",
            "protocol",
            "run",
            "evidence",
            "review",
            "reproduce",
            "execute",
            "release",
        ],
    }


def save_dmp(
    actor: ActorContext, project_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_write(actor)
    supplied = payload.get("content")
    content = dict(supplied) if isinstance(supplied, dict) else {
        key: payload.get(key) for key in DMP_FIELDS if key in payload
    }
    if not any(str(value or "").strip() for value in content.values()):
        raise HTTPException(status_code=422, detail="DMP content is required")
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref, lock=True)
        current = (
            session.execute(
                text(
                    """
                    SELECT * FROM research.dmp_revisions
                    WHERE project_id = :project_id
                    ORDER BY version DESC LIMIT 1 FOR UPDATE
                    """
                ),
                {"project_id": project["id"]},
            )
            .mappings()
            .one_or_none()
        )
        merged = dict(current["content"]) if current else {}
        merged.update(content)
        version = int(current["version"]) + 1 if current else 1
        if current:
            session.execute(
                text(
                    """
                    UPDATE research.dmp_revisions SET status = 'superseded'
                    WHERE id = :id AND status <> 'superseded'
                    """
                ),
                {"id": current["id"]},
            )
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.dmp_revisions(
                      id, tenant_id, project_id, version, status, content, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :version, 'draft',
                      CAST(:content AS jsonb), :created_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "version": version,
                    "content": _canonical(merged),
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.dmp.versioned",
            {"project_id": project["id"], "dmp_id": row["id"], "version": version},
        )
    return {"ok": True, "dmp": _json_safe(dict(row))}


def create_protocol(
    actor: ActorContext, project_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_write(actor)
    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")
    protocol_status = str(payload.get("status") or "draft")
    if protocol_status not in PROTOCOL_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid protocol status")
    if protocol_status == "locked":
        _require_review(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref, lock=True)
        number = int(
            session.execute(
                text(
                    "SELECT count(*) FROM research.protocols "
                    "WHERE project_id = :project_id"
                ),
                {"project_id": project["id"]},
            ).scalar_one()
        ) + 1
        code = str(payload.get("protocol_code") or f"PRO-{number:03d}").strip()
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.protocols(
                      id, tenant_id, project_id, protocol_code, title, objective,
                      status, specification, locked_at, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :code, :title, :objective,
                      :status, CAST(:specification AS jsonb),
                      CASE WHEN :status = 'locked' THEN now() ELSE NULL END,
                      :created_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "code": code,
                    "title": title,
                    "objective": str(payload.get("objective") or "").strip() or None,
                    "status": protocol_status,
                    "specification": _canonical(_payload_dict(payload, "specification")),
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.protocol.created",
            {"project_id": project["id"], "protocol_id": row["id"], "code": code},
        )
    return {"ok": True, "protocol": _json_safe(dict(row))}


def create_run(
    actor: ActorContext, project_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_write(actor)
    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")
    run_status = str(payload.get("status") or "running")
    if run_status not in RUN_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid run status")
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref, lock=True)
        protocol_id = None
        if payload.get("protocol_id"):
            protocol = _row_by_id(
                session,
                "research.protocols",
                project["id"],
                payload["protocol_id"],
                label="protocol",
            )
            protocol_id = protocol["id"]
        code = str(
            payload.get("run_code")
            or f"RUN-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        ).strip()
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.runs(
                      id, tenant_id, project_id, run_code, protocol_id, title,
                      status, inputs, environment, observations, deviation_note,
                      started_at, completed_at, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :code, :protocol_id, :title,
                      :status, CAST(:inputs AS jsonb), CAST(:environment AS jsonb),
                      CAST(:observations AS jsonb), :deviation_note,
                      CASE WHEN :status IN ('running','completed','failed') THEN now() END,
                      CASE WHEN :status IN ('completed','failed','cancelled') THEN now() END,
                      :created_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "code": code,
                    "protocol_id": protocol_id,
                    "title": title,
                    "status": run_status,
                    "inputs": _canonical(_payload_dict(payload, "inputs")),
                    "environment": _canonical(_payload_dict(payload, "environment")),
                    "observations": _canonical(_payload_dict(payload, "observations")),
                    "deviation_note": str(payload.get("deviation_note") or "").strip()
                    or None,
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.run.created",
            {"project_id": project["id"], "run_id": row["id"], "code": code},
        )
    return {"ok": True, "run": _json_safe(dict(row))}


def update_run(
    actor: ActorContext,
    project_ref: object,
    run_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_write(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        current = _row_by_id(
            session,
            "research.runs",
            project["id"],
            run_ref,
            label="run",
            lock=True,
        )
        run_status = str(payload.get("status") or current["status"])
        if run_status not in RUN_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid run status")
        values: dict[str, object] = {}
        for key in ("inputs", "environment", "observations"):
            existing = dict(current[key] or {})
            if isinstance(payload.get(key), dict):
                existing.update(payload[key])  # type: ignore[arg-type]
            values[key] = _canonical(existing)
        row = (
            session.execute(
                text(
                    """
                    UPDATE research.runs
                    SET status = :status,
                        inputs = CAST(:inputs AS jsonb),
                        environment = CAST(:environment AS jsonb),
                        observations = CAST(:observations AS jsonb),
                        deviation_note = :deviation_note,
                        started_at = CASE
                          WHEN started_at IS NULL
                           AND :status IN ('running','completed','failed') THEN now()
                          ELSE started_at END,
                        completed_at = CASE
                          WHEN :status IN ('completed','failed','cancelled') THEN
                            COALESCE(completed_at, now())
                          ELSE NULL END
                    WHERE id = :id
                    RETURNING *
                    """
                ),
                {
                    "id": current["id"],
                    "status": run_status,
                    **values,
                    "deviation_note": (
                        str(payload.get("deviation_note")).strip()
                        if "deviation_note" in payload
                        else current["deviation_note"]
                    )
                    or None,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.run.updated",
            {
                "project_id": project["id"],
                "run_id": current["id"],
                "status": run_status,
            },
        )
    return {"ok": True, "run": _json_safe(dict(row))}


def create_claim(
    actor: ActorContext, project_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_write(actor)
    statement = str(payload.get("statement") or "").strip()
    if not statement:
        raise HTTPException(status_code=422, detail="statement is required")
    claim_status = str(payload.get("status") or "submitted")
    if claim_status not in CLAIM_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid claim status")
    confidence = payload.get("confidence")
    if confidence not in (None, ""):
        try:
            confidence = float(confidence)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Invalid confidence") from exc
        if not 0 <= confidence <= 1:
            raise HTTPException(status_code=422, detail="confidence must be 0-1")
    else:
        confidence = None
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref, lock=True)
        number = int(
            session.execute(
                text(
                    "SELECT count(*) FROM research.claims "
                    "WHERE project_id = :project_id"
                ),
                {"project_id": project["id"]},
            ).scalar_one()
        ) + 1
        code = str(payload.get("claim_code") or f"CLM-{number:03d}").strip()
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.claims(
                      id, tenant_id, project_id, claim_code, statement, status,
                      confidence, metadata, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :code, :statement, :status,
                      :confidence, CAST(:metadata AS jsonb), :created_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "code": code,
                    "statement": statement,
                    "status": claim_status,
                    "confidence": confidence,
                    "metadata": _canonical(_payload_dict(payload, "metadata")),
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.claim.created",
            {"project_id": project["id"], "claim_id": row["id"], "code": code},
        )
    return {"ok": True, "claim": _json_safe(dict(row))}


def link_claim_evidence(
    actor: ActorContext,
    project_ref: object,
    claim_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_write(actor)
    relation = str(payload.get("relation") or "supports")
    if relation not in EVIDENCE_RELATIONS:
        raise HTTPException(status_code=422, detail="Invalid evidence relation")
    file_version_id = payload.get("file_version_id")
    run_id = payload.get("run_id")
    if bool(file_version_id) == bool(run_id):
        raise HTTPException(
            status_code=422,
            detail="Exactly one of file_version_id or run_id is required",
        )
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        claim = _row_by_id(
            session,
            "research.claims",
            project["id"],
            claim_ref,
            label="claim",
        )
        version_uuid = None
        run_uuid = None
        if file_version_id:
            version = _row_by_id(
                session,
                "research.file_versions",
                project["id"],
                file_version_id,
                label="file version",
            )
            version_uuid = version["id"]
        else:
            run = _row_by_id(
                session,
                "research.runs",
                project["id"],
                run_id,
                label="run",
            )
            run_uuid = run["id"]
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.claim_evidence(
                      id, tenant_id, project_id, claim_id, file_version_id,
                      run_id, relation, note, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :claim_id, :file_version_id,
                      :run_id, :relation, :note, :created_by
                    )
                    ON CONFLICT (
                      tenant_id, project_id, claim_id, file_version_id, run_id, relation
                    ) DO UPDATE
                      SET note = EXCLUDED.note
                    RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "claim_id": claim["id"],
                    "file_version_id": version_uuid,
                    "run_id": run_uuid,
                    "relation": relation,
                    "note": str(payload.get("note") or "").strip() or None,
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.claim.evidence_linked",
            {
                "project_id": project["id"],
                "claim_id": claim["id"],
                "evidence_id": row["id"],
                "relation": relation,
            },
        )
    return {"ok": True, "evidence": _json_safe(dict(row))}


def submit_review(
    actor: ActorContext, project_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_review(actor)
    target_type = str(payload.get("target_type") or "")
    decision = str(payload.get("decision") or "")
    if target_type not in REVIEW_TARGETS:
        raise HTTPException(status_code=422, detail="Invalid review target type")
    if decision not in REVIEW_DECISIONS:
        raise HTTPException(status_code=422, detail="Invalid review decision")
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        target = _row_by_id(
            session,
            REVIEW_TARGETS[target_type][0],
            project["id"],
            payload.get("target_id"),
            label=target_type,
            lock=True,
        )
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.reviews(
                      id, tenant_id, project_id, target_type, target_id,
                      decision, comment, metadata, reviewer_id
                    ) VALUES (
                      :id, :tenant_id, :project_id, :target_type, :target_id,
                      :decision, :comment, CAST(:metadata AS jsonb), :reviewer_id
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "target_type": target_type,
                    "target_id": target["id"],
                    "decision": decision,
                    "comment": str(payload.get("comment") or "").strip(),
                    "metadata": _canonical(_payload_dict(payload, "metadata")),
                    "reviewer_id": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        if target_type == "dmp" and decision == "approve":
            session.execute(
                text(
                    """
                    UPDATE research.dmp_revisions
                    SET status = CASE WHEN id = :id THEN 'approved' ELSE 'superseded' END
                    WHERE project_id = :project_id AND status <> 'superseded'
                    """
                ),
                {"id": target["id"], "project_id": project["id"]},
            )
        elif target_type == "protocol" and decision == "approve":
            session.execute(
                text(
                    """
                    UPDATE research.protocols
                    SET status = 'locked', locked_at = COALESCE(locked_at, now())
                    WHERE id = :id
                    """
                ),
                {"id": target["id"]},
            )
        elif target_type == "claim" and decision != "comment":
            next_status = {
                "approve": "accepted",
                "changes_requested": "changes_requested",
                "reject": "rejected",
            }[decision]
            session.execute(
                text("UPDATE research.claims SET status = :status WHERE id = :id"),
                {"status": next_status, "id": target["id"]},
            )
        _audit(
            session,
            actor,
            "research.review.submitted",
            {
                "project_id": project["id"],
                "review_id": row["id"],
                "target_type": target_type,
                "target_id": target["id"],
                "decision": decision,
            },
        )
    return {"ok": True, "review": _json_safe(dict(row))}


def _reproduction_manifest(
    session: Session, project: dict[str, object]
) -> tuple[dict[str, object], list[dict[str, str]]]:
    latest_dmp = (
        session.execute(
            text(
                """
                SELECT id, version, status, content
                FROM research.dmp_revisions
                WHERE project_id = :project_id
                ORDER BY version DESC LIMIT 1
                """
            ),
            {"project_id": project["id"]},
        )
        .mappings()
        .one_or_none()
    )
    protocols = (
        session.execute(
            text(
                """
                SELECT id, protocol_code, version, status, specification
                FROM research.protocols WHERE project_id = :project_id
                ORDER BY created_at
                """
            ),
            {"project_id": project["id"]},
        )
        .mappings()
        .all()
    )
    runs = (
        session.execute(
            text(
                """
                SELECT id, run_code, protocol_id, status, inputs, environment,
                       observations, deviation_note
                FROM research.runs WHERE project_id = :project_id
                ORDER BY created_at
                """
            ),
            {"project_id": project["id"]},
        )
        .mappings()
        .all()
    )
    files = (
        session.execute(
            text(
                """
                SELECT f.id, f.logical_path, v.id AS version_id, v.version,
                       v.content_sha256, v.git_sha, v.content_type
                FROM research.files f
                JOIN LATERAL (
                  SELECT * FROM research.file_versions
                  WHERE file_id = f.id ORDER BY version DESC LIMIT 1
                ) v ON true
                WHERE f.project_id = :project_id AND f.status = 'active'
                ORDER BY f.logical_path
                """
            ),
            {"project_id": project["id"]},
        )
        .mappings()
        .all()
    )
    claims = (
        session.execute(
            text(
                """
                SELECT c.id, c.claim_code, c.statement, c.status,
                       COALESCE(jsonb_agg(
                         jsonb_build_object(
                           'relation', e.relation,
                           'file_version_id', e.file_version_id,
                           'run_id', e.run_id
                         )
                       ) FILTER (WHERE e.id IS NOT NULL), '[]'::jsonb) AS evidence
                FROM research.claims c
                LEFT JOIN research.claim_evidence e ON e.claim_id = c.id
                WHERE c.project_id = :project_id
                GROUP BY c.id
                ORDER BY c.created_at
                """
            ),
            {"project_id": project["id"]},
        )
        .mappings()
        .all()
    )
    findings: list[dict[str, str]] = []
    if latest_dmp is None:
        findings.append({"severity": "warning", "code": "DMP_MISSING"})
    else:
        missing = [
            key
            for key in DMP_FIELDS
            if not str(dict(latest_dmp["content"] or {}).get(key) or "").strip()
        ]
        if missing:
            findings.append(
                {
                    "severity": "warning",
                    "code": "DMP_INCOMPLETE",
                    "detail": ", ".join(missing),
                }
            )
        if latest_dmp["status"] != "approved":
            findings.append({"severity": "warning", "code": "DMP_NOT_APPROVED"})
    if not any(row["status"] == "locked" for row in protocols):
        findings.append({"severity": "warning", "code": "NO_LOCKED_PROTOCOL"})
    completed_runs = [row for row in runs if row["status"] == "completed"]
    if not completed_runs:
        findings.append({"severity": "error", "code": "NO_COMPLETED_RUN"})
    for row in completed_runs:
        if not row["environment"]:
            findings.append(
                {
                    "severity": "warning",
                    "code": "RUN_ENVIRONMENT_MISSING",
                    "detail": str(row["run_code"]),
                }
            )
    if not claims:
        findings.append({"severity": "error", "code": "NO_CLAIMS"})
    for row in claims:
        if not row["evidence"]:
            findings.append(
                {
                    "severity": "error",
                    "code": "CLAIM_WITHOUT_EVIDENCE",
                    "detail": str(row["claim_code"]),
                }
            )
    manifest = {
        "schema": "warehouse-research-manifest/1.0",
        "generated_at": datetime.now().isoformat(),
        "project": {
            "id": project["id"],
            "slug": project["slug"],
            "title": project["title"],
            "head_git_sha": project["head_git_sha"],
        },
        "dmp": dict(latest_dmp) if latest_dmp else None,
        "protocols": [dict(row) for row in protocols],
        "runs": [dict(row) for row in runs],
        "files": [dict(row) for row in files],
        "claims": [dict(row) for row in claims],
    }
    return _json_safe(manifest), findings  # type: ignore[return-value]


def run_reproduction_check(
    actor: ActorContext, project_ref: object
) -> dict[str, object]:
    _require_write(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        manifest, findings = _reproduction_manifest(session, project)
        check_status = (
            "failed"
            if any(item["severity"] == "error" for item in findings)
            else "warning" if findings else "passed"
        )
        manifest_sha256 = _digest(manifest)
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.reproduction_checks(
                      id, tenant_id, project_id, status, manifest, findings,
                      manifest_sha256, executed_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :status,
                      CAST(:manifest AS jsonb), CAST(:findings AS jsonb),
                      :manifest_sha256, :executed_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "status": check_status,
                    "manifest": _canonical(manifest),
                    "findings": _canonical(findings),
                    "manifest_sha256": manifest_sha256,
                    "executed_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.reproduction.checked",
            {
                "project_id": project["id"],
                "check_id": row["id"],
                "status": check_status,
                "manifest_sha256": manifest_sha256,
            },
        )
    return {"ok": True, "check": _json_safe(dict(row))}


def _ro_crate(
    actor: ActorContext,
    project: dict[str, object],
    manifest: dict[str, object],
    release_code: str,
    title: str,
    license_name: str | None,
) -> dict[str, object]:
    project_node = {
        "@id": "./",
        "@type": "Dataset",
        "name": title,
        "identifier": release_code,
        "description": project.get("summary") or "",
        "license": license_name or "NOASSERTION",
        "hasPart": [
            {"@id": f"objects/{item['version_id']}"}
            for item in manifest.get("files", [])
        ],
    }
    graph: list[dict[str, object]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": "./"},
            "conformsTo": {
                "@id": "https://w3id.org/ro/crate/1.2"
            },
        },
        project_node,
        {
            "@id": f"people/{actor.user_id}",
            "@type": "Person",
            "name": actor.display_name,
        },
    ]
    for item in manifest.get("files", []):
        graph.append(
            {
                "@id": f"objects/{item['version_id']}",
                "@type": "File",
                "name": item["logical_path"],
                "encodingFormat": item["content_type"],
                "sha256": item["content_sha256"],
                "version": str(item["version"]),
            }
        )
    for item in manifest.get("runs", []):
        graph.append(
            {
                "@id": f"runs/{item['id']}",
                "@type": "CreateAction",
                "name": item["run_code"],
                "actionStatus": item["status"],
            }
        )
    for item in manifest.get("claims", []):
        graph.append(
            {
                "@id": f"claims/{item['id']}",
                "@type": "Claim",
                "identifier": item["claim_code"],
                "text": item["statement"],
            }
        )
    return {
        "@context": "https://w3id.org/ro/crate/1.2/context",
        "@graph": graph,
    }


def create_release(
    actor: ActorContext, project_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_review(actor)
    access_level = str(payload.get("access_level") or "restricted")
    if access_level not in {"open", "embargoed", "restricted"}:
        raise HTTPException(status_code=422, detail="Invalid access level")
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref, lock=True)
        latest_check = (
            session.execute(
                text(
                    """
                    SELECT * FROM research.reproduction_checks
                    WHERE project_id = :project_id
                    ORDER BY executed_at DESC LIMIT 1
                    """
                ),
                {"project_id": project["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if latest_check is None or latest_check["status"] != "passed":
            raise HTTPException(
                status_code=409,
                detail="A passed reproducibility check is required before release",
            )
        accepted_claims = int(
            session.execute(
                text(
                    """
                    SELECT count(*) FROM research.claims
                    WHERE project_id = :project_id AND status = 'accepted'
                    """
                ),
                {"project_id": project["id"]},
            ).scalar_one()
        )
        if accepted_claims == 0:
            raise HTTPException(
                status_code=409,
                detail="At least one reviewed and accepted claim is required",
            )
        version = int(
            session.execute(
                text(
                    "SELECT count(*) FROM research.releases "
                    "WHERE project_id = :project_id"
                ),
                {"project_id": project["id"]},
            ).scalar_one()
        ) + 1
        release_code = f"{project['slug']}/v{version}"
        title = str(payload.get("title") or f"{project['title']} · Release {version}").strip()
        manifest = dict(latest_check["manifest"])
        manifest["release"] = {
            "code": release_code,
            "version": version,
            "access_level": access_level,
            "created_at": datetime.now().isoformat(),
        }
        manifest_sha256 = _digest(manifest)
        license_name = str(payload.get("license") or "").strip() or None
        ro_crate = _ro_crate(
            actor, project, manifest, release_code, title, license_name
        )
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.releases(
                      id, tenant_id, project_id, release_code, version, title,
                      description, status, access_level, license, embargo_until,
                      manifest, manifest_sha256, ro_crate, created_by, released_by,
                      released_at
                    ) VALUES (
                      :id, :tenant_id, :project_id, :release_code, :version, :title,
                      :description, 'published', :access_level, :license,
                      :embargo_until, CAST(:manifest AS jsonb), :manifest_sha256,
                      CAST(:ro_crate AS jsonb), :created_by, :released_by, now()
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "release_code": release_code,
                    "version": version,
                    "title": title,
                    "description": str(payload.get("description") or "").strip()
                    or None,
                    "access_level": access_level,
                    "license": license_name,
                    "embargo_until": payload.get("embargo_until") or None,
                    "manifest": _canonical(manifest),
                    "manifest_sha256": manifest_sha256,
                    "ro_crate": _canonical(ro_crate),
                    "created_by": actor.user_id,
                    "released_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.release.published",
            {
                "project_id": project["id"],
                "release_id": row["id"],
                "release_code": release_code,
                "manifest_sha256": manifest_sha256,
            },
        )
    return {"ok": True, "release": _json_safe(dict(row))}


def release_detail(
    actor: ActorContext, project_ref: object, release_ref: object
) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        identifier = _uuid(release_ref)
        clause = "id = :value" if identifier else "release_code = :value"
        row = (
            session.execute(
                text(
                    f"""
                    SELECT * FROM research.releases
                    WHERE project_id = :project_id AND {clause}
                    """
                ),
                {"project_id": project["id"], "value": identifier or str(release_ref)},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="release not found")
    return {"source": "research_release", "release": _json_safe(dict(row))}
