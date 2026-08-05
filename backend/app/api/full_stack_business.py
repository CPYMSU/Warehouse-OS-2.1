# ruff: noqa: E501
"""Functional PostgreSQL compatibility for retained business pages."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.api.full_stack_identity import _audit, _doc, _docs, _safe, _upsert_doc
from app.core.config import Settings, get_settings
from app.db.session import system_session, tenant_session

router = APIRouter(tags=["full-stack-business"])


DEFAULT_CASE_TYPE = {
    "id": "general",
    "key": "general",
    "name": "通用事务",
    "category": "service",
    "description": "通用登记、分派、处理与结案流程",
    "owner_unit_code": "",
    "default_severity": "medium",
    "confidentiality": "internal",
    "active": True,
    "pause_sla_on_waiting": True,
    "revision_no": 1,
    "fields": [],
    "metrics": ["first_response", "resolution_time", "sla_hit", "backlog"],
    "sla": {
        "clock_mode": "calendar",
        "levels": {
            "critical": {"response_minutes": 5, "resolution_minutes": 60},
            "high": {"response_minutes": 15, "resolution_minutes": 240},
            "medium": {"response_minutes": 60, "resolution_minutes": 480},
            "low": {"response_minutes": 240, "resolution_minutes": 1440},
        },
    },
}

DEFAULT_RECORD_TYPES = [
    {
        "id": "general_record",
        "key": "general_record",
        "type_key": "general_record",
        "name": "通用档案",
        "category_key": "other",
        "initial_status": "draft",
        "default_confidentiality": "internal",
        "active": True,
        "can_create": True,
        "revision_no": 1,
        "fields": [],
    },
    {
        "id": "personnel_record",
        "key": "personnel_record",
        "type_key": "personnel_record",
        "name": "人员档案",
        "category_key": "personnel",
        "initial_status": "active",
        "default_confidentiality": "internal",
        "active": True,
        "can_create": True,
        "revision_no": 1,
        "fields": [],
    },
]

RECORD_CATEGORIES = [
    {"key": "personnel", "name": "人员档案", "icon": "user", "order": 10},
    {"key": "meeting", "name": "会议档案", "icon": "clipboard", "order": 20},
    {"key": "training", "name": "培训档案", "icon": "doc", "order": 30},
    {"key": "safety", "name": "安全档案", "icon": "shield", "order": 40},
    {"key": "case", "name": "事务档案", "icon": "layers", "order": 50},
    {"key": "other", "name": "其他档案", "icon": "box", "order": 60},
]

RECORD_CONFIG_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
RECORD_TYPE_CONFIG_KEYS = frozenset(
    {
        "key", "category_key", "name", "description", "lifecycle_mode",
        "owner_unit_code", "confidentiality", "fields", "statuses",
        "initial_status", "terminal_statuses", "transitions", "reminders",
        "retention",
    }
)
RECORD_CATEGORY_CONFIG_KEYS = frozenset(
    {
        "key", "name", "description", "icon", "order", "owner_unit_code",
        "confidentiality", "retention",
    }
)


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _blob_insert(
    actor: ActorContext,
    *,
    namespace: str,
    entity_key: str,
    field_key: str | None,
    file_name: str,
    content_type: str,
    content: bytes,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    blob_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                INSERT INTO compatibility.blobs(
                  id, tenant_id, namespace, entity_key, field_key,
                  file_name, content_type, content, metadata, created_by
                ) VALUES (
                  :id, :tenant_id, :namespace, :entity_key, :field_key,
                  :file_name, :content_type, :content, CAST(:metadata AS jsonb), :created_by
                )
                RETURNING id, file_name, content_type, octet_length(content) AS file_size,
                          field_key, metadata, created_at
                """
            ),
            {
                "id": blob_id,
                "tenant_id": actor.tenant_id,
                "namespace": namespace,
                "entity_key": entity_key,
                "field_key": field_key,
                "file_name": file_name,
                "content_type": content_type or "application/octet-stream",
                "content": content,
                "metadata": json.dumps(metadata or {}, ensure_ascii=False),
                "created_by": actor.user_id,
            },
        ).mappings().one()
        _audit(
            session,
            actor,
            "compatibility.blob.created",
            {"namespace": namespace, "entity_key": entity_key, "blob_id": str(blob_id)},
        )
    return _safe(dict(row))


def _blob_response(actor: ActorContext, blob_id: str) -> Response:
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                SELECT file_name, content_type, content
                FROM compatibility.blobs WHERE id = :id
                """
            ),
            {"id": UUID(blob_id)},
        ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_name = str(row["file_name"]).replace("\r", "").replace("\n", "")
    extension = Path(file_name).suffix
    ascii_name = f"workflow-attachment{extension}" if extension else "workflow-attachment"
    return Response(
        content=bytes(row["content"]),
        media_type=row["content_type"],
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_name}"; '
                f"filename*=UTF-8''{quote(file_name, safe='')}"
            )
        },
    )


WORKFLOW_ATTACHMENT_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".doc",
        ".docx",
        ".rtf",
        ".odt",
        ".xls",
        ".xlsx",
        ".ods",
        ".csv",
        ".ppt",
        ".pptx",
        ".odp",
        ".txt",
        ".md",
        ".json",
        ".xml",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".tif",
        ".tiff",
        ".zip",
        ".7z",
        ".rar",
    }
)


def _workflow_attachment_permission(actor: ActorContext) -> None:
    if actor.role_level >= 10:
        return
    if actor.permissions.intersection(
        {
            "procurement.workflow.use",
            "procurement.workflow.admin",
            "procurement.global.act",
            "workflow.manage",
        }
    ):
        return
    raise HTTPException(status_code=403, detail="No permission to notarize workflow attachments")


def _workflow_attachment_file(
    file: UploadFile,
    content: bytes,
    settings: Settings,
) -> tuple[str, str]:
    file_name = (
        Path(file.filename or "").name.replace("\r", "").replace("\n", "").strip()
    )
    if not file_name or file_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="A file name is required")
    extension = Path(file_name).suffix.lower()
    if extension not in WORKFLOW_ATTACHMENT_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported workflow attachment type: {extension or 'unknown'}",
        )
    if not content:
        raise HTTPException(status_code=400, detail="The attachment is empty")
    if len(content) > settings.workflow_attachment_max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                "Workflow attachment exceeds "
                f"{settings.workflow_attachment_max_upload_bytes // (1024 * 1024)}MB"
            ),
        )
    return file_name[:240], (file.content_type or "application/octet-stream")[:160]


def _workflow_attachment_material(row: dict[str, object]) -> bytes:
    created_at = row["created_at"]
    if not isinstance(created_at, datetime):
        created_at = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    created_at = (
        created_at.astimezone(UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
    payload = {
        "attachment_id": str(row["id"]),
        "attachment_key": str(row["attachment_key"]),
        "tenant_id": str(row["tenant_id"]),
        "instance_id": str(row["instance_id"]),
        "node_key": str(row["node_key"]),
        "kind": str(row["kind"]),
        "version": int(row["version"]),
        "file_name": str(row["file_name"]),
        "content_type": str(row["content_type"]),
        "size_bytes": int(row["size_bytes"]),
        "content_sha256": str(row["content_sha256"]),
        "previous_event_hash": (
            str(row["previous_event_hash"]) if row.get("previous_event_hash") else None
        ),
        "uploaded_by": str(row["uploaded_by"]),
        "created_at": str(created_at),
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _workflow_attachment_public(row: dict[str, object]) -> dict[str, object]:
    data = _safe(dict(row))
    attachment_id = str(data["id"])
    return {
        **data,
        "file_size": data["size_bytes"],
        "file_sha256": data["content_sha256"],
        "file_seal": data["notary_serial"],
        "has_file": True,
        "notarized": True,
        "verification_status": "sealed",
        "download_url": f"/api/wf/artifacts/{attachment_id}/download",
        "verify_url": f"/api/wf/node-attachments/{attachment_id}/verify",
    }


def _store_workflow_node_attachment(
    actor: ActorContext,
    settings: Settings,
    *,
    instance_id: UUID,
    node_key: str,
    kind: str,
    file_name: str,
    content_type: str,
    content: bytes,
    expected_sha256: str | None = None,
    attachment_key: UUID | None = None,
) -> dict[str, object]:
    _workflow_attachment_permission(actor)
    node_key = node_key.strip()
    kind = (kind.strip() or "node_attachment")[:120]
    if not node_key:
        raise HTTPException(status_code=400, detail="A workflow node key is required")
    content_sha256 = hashlib.sha256(content).hexdigest()
    if expected_sha256 and not hmac.compare_digest(
        expected_sha256.strip().lower(), content_sha256
    ):
        raise HTTPException(status_code=409, detail="Attachment SHA-256 does not match")

    with tenant_session(actor.tenant_id) as session:
        instance = session.execute(
            text(
                """
                SELECT wi.id, wd.definition
                FROM workflow.instances AS wi
                JOIN workflow.definitions AS wd
                  ON wd.tenant_id = wi.tenant_id AND wd.id = wi.definition_id
                WHERE wi.id = :instance_id
                """
            ),
            {"instance_id": instance_id},
        ).mappings().one_or_none()
        if instance is None:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        definition = instance["definition"] if isinstance(instance["definition"], dict) else {}
        node_keys = {
            str(node.get("node_key"))
            for node in definition.get("nodes", [])
            if isinstance(node, dict) and node.get("node_key")
        }
        if node_key not in node_keys:
            raise HTTPException(status_code=404, detail="Workflow node not found")

        logical_key = attachment_key or uuid4()
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {
                "lock_key": (
                    f"{actor.tenant_id}:{instance_id}:{node_key}:{logical_key}"
                )
            },
        )
        previous = session.execute(
            text(
                """
                SELECT version, event_hash
                FROM workflow.node_attachments
                WHERE instance_id = :instance_id
                  AND node_key = :node_key
                  AND attachment_key = :attachment_key
                ORDER BY version DESC
                LIMIT 1
                FOR UPDATE
                """
            ),
            {
                "instance_id": instance_id,
                "node_key": node_key,
                "attachment_key": logical_key,
            },
        ).mappings().one_or_none()
        version = int(previous["version"]) + 1 if previous else 1
        previous_event_hash = str(previous["event_hash"]) if previous else None
        attachment_id = uuid4()
        blob_id = uuid4()
        created_at = datetime.now(UTC)
        notary_row: dict[str, object] = {
            "id": attachment_id,
            "tenant_id": actor.tenant_id,
            "instance_id": instance_id,
            "node_key": node_key,
            "attachment_key": logical_key,
            "kind": kind,
            "version": version,
            "file_name": file_name,
            "content_type": content_type,
            "size_bytes": len(content),
            "content_sha256": content_sha256,
            "previous_event_hash": previous_event_hash,
            "uploaded_by": actor.user_id,
            "created_at": created_at,
        }
        event_hash = hashlib.sha256(_workflow_attachment_material(notary_row)).hexdigest()
        notary_signature = hmac.new(
            settings.integration_secret.encode("utf-8"),
            event_hash.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        notary_serial = (
            f"WFN-{created_at:%Y%m%d}-{event_hash[:12].upper()}-"
            f"{str(attachment_id)[:8].upper()}"
        )
        metadata = {
            "instance_id": str(instance_id),
            "node_key": node_key,
            "attachment_key": str(logical_key),
            "kind": kind,
            "version": version,
            "content_sha256": content_sha256,
            "event_hash": event_hash,
            "notary_serial": notary_serial,
        }
        session.execute(
            text(
                """
                INSERT INTO compatibility.blobs(
                  id, tenant_id, namespace, entity_key, field_key,
                  file_name, content_type, content, metadata, created_by, created_at
                ) VALUES (
                  :id, :tenant_id, 'workflow.node_attachment', :entity_key, :field_key,
                  :file_name, :content_type, :content, CAST(:metadata AS jsonb),
                  :created_by, :created_at
                )
                """
            ),
            {
                "id": blob_id,
                "tenant_id": actor.tenant_id,
                "entity_key": str(instance_id),
                "field_key": node_key,
                "file_name": file_name,
                "content_type": content_type,
                "content": content,
                "metadata": json.dumps(metadata, ensure_ascii=False),
                "created_by": actor.user_id,
                "created_at": created_at,
            },
        )
        row = session.execute(
            text(
                """
                INSERT INTO workflow.node_attachments(
                  id, tenant_id, instance_id, node_key, attachment_key, kind,
                  version, blob_id, file_name, content_type, size_bytes,
                  content_sha256, previous_event_hash, event_hash,
                  notary_serial, notary_signature, uploaded_by, created_at
                ) VALUES (
                  :id, :tenant_id, :instance_id, :node_key, :attachment_key, :kind,
                  :version, :blob_id, :file_name, :content_type, :size_bytes,
                  :content_sha256, :previous_event_hash, :event_hash,
                  :notary_serial, :notary_signature, :uploaded_by, :created_at
                )
                RETURNING *
                """
            ),
            {
                **notary_row,
                "blob_id": blob_id,
                "event_hash": event_hash,
                "notary_serial": notary_serial,
                "notary_signature": notary_signature,
            },
        ).mappings().one()
        _audit(
            session,
            actor,
            "workflow.node_attachment.notarized",
            {
                "attachment_id": str(attachment_id),
                "instance_id": str(instance_id),
                "node_key": node_key,
                "version": version,
                "content_sha256": content_sha256,
                "event_hash": event_hash,
                "notary_serial": notary_serial,
            },
        )
    return _workflow_attachment_public(dict(row))


def _tenant_people(actor: ActorContext) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    with tenant_session(actor.tenant_id) as session:
        units = session.execute(
            text(
                """
                SELECT id, unit_code, name AS unit_name, unit_type, parent_unit_code
                FROM iam.organizational_units WHERE active ORDER BY name
                """
            )
        ).mappings().all()
        users = session.execute(
            text(
                """
                SELECT u.id, u.username, u.display_name, m.position_code,
                       pp.department_code AS unit_code, ou.name AS unit_name
                FROM iam.memberships AS m
                JOIN iam.users AS u ON u.id = m.user_id
                LEFT JOIN iam.position_profiles AS pp
                  ON pp.tenant_id = m.tenant_id AND pp.position_code = m.position_code
                LEFT JOIN iam.organizational_units AS ou
                  ON ou.tenant_id = pp.tenant_id AND ou.unit_code = pp.department_code
                WHERE m.active AND u.active ORDER BY u.display_name, u.username
                """
            )
        ).mappings().all()
    return ([_safe(dict(row)) for row in units], [_safe(dict(row)) for row in users])


# ---------------------------------------------------------------------------
# Cases


def _case_types(actor: ActorContext) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = _docs(session, "case.type", 500)
    return rows or [dict(DEFAULT_CASE_TYPE)]


def _case_actions(case: dict[str, object]) -> list[str]:
    status_value = str(case.get("status") or "submitted")
    mapping = {
        "draft": ["submit", "cancel"],
        "submitted": ["triage", "assign", "cancel"],
        "triaged": ["assign", "start", "cancel"],
        "assigned": ["start", "wait", "resolve", "cancel"],
        "in_progress": ["wait", "review", "resolve", "cancel"],
        "waiting_external": ["resume", "resolve", "cancel"],
        "pending_review": ["resume", "resolve", "cancel"],
        "resolved": ["close", "reopen"],
        "closed": ["reopen"],
        "cancelled": ["reopen"],
    }
    return mapping.get(status_value, ["start", "resolve", "close"])


def _case_enrich(actor: ActorContext, case: dict[str, object]) -> dict[str, object]:
    result = dict(case)
    types = _case_types(actor)
    type_key = str(result.get("type_id") or result.get("type_key") or "general")
    type_config = next(
        (
            row
            for row in types
            if str(row.get("id")) == type_key or str(row.get("key")) == type_key
        ),
        dict(DEFAULT_CASE_TYPE),
    )
    result.setdefault("type_config", type_config)
    result.setdefault("type_name_snapshot", type_config.get("name") or "通用事务")
    result.setdefault("owner_unit_code_snapshot", type_config.get("owner_unit_code") or "")
    result.setdefault("owner_unit_name", type_config.get("owner_unit_name") or "")
    result.setdefault("dynamic_data", result.get("fields") or {})
    result.setdefault("attachments", [])
    result.setdefault("events", [])
    result.setdefault("lock_version", 1)
    result["capabilities"] = {
        "available_actions": _case_actions(result),
        "can_process": True,
        "can_assign": True,
        "can_close": True,
    }
    due = result.get("resolution_due_at")
    try:
        result["overdue"] = bool(due and datetime.fromisoformat(str(due)) < datetime.now(UTC))
    except ValueError:
        result["overdue"] = False
    return _safe(result)


def _case_get(actor: ActorContext, case_id: str) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = _doc(session, "case", case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_enrich(actor, row)


@router.get("/api/cases/meta")
def cases_meta(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    units, users = _tenant_people(actor)
    types = _case_types(actor)
    return {
        "types": [row for row in types if row.get("active", True)],
        "config_types": types,
        "units": units,
        "assignees": users,
        "permissions": {
            "can_create": True,
            "can_analyze": True,
            "can_configure": True,
        },
    }


@router.post("/api/cases", status_code=201)
def cases_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    case_id = str(uuid4())
    created_at = _iso_now()
    case = {
        "id": case_id,
        "case_no": f"CASE-{datetime.now(UTC):%Y%m%d}-{case_id[:8].upper()}",
        "type_id": str(payload.get("type_id") or payload.get("type_key") or "general"),
        "title": str(payload.get("title") or "Untitled case")[:240],
        "description": str(payload.get("description") or ""),
        "severity": str(payload.get("severity") or "medium"),
        "status": "submitted",
        "occurred_at": payload.get("occurred_at") or created_at,
        "location_text": payload.get("location") or payload.get("location_text") or "",
        "dynamic_data": payload.get("fields") if isinstance(payload.get("fields"), dict) else {},
        "reporter_user_id": str(actor.user_id),
        "reporter_name": actor.display_name,
        "assignee_user_id": None,
        "assignee_name": None,
        "response_due_at": (datetime.now(UTC) + timedelta(minutes=60)).isoformat(),
        "resolution_due_at": (datetime.now(UTC) + timedelta(minutes=480)).isoformat(),
        "created_at": created_at,
        "updated_at": created_at,
        "lock_version": 1,
        "events": [
            {
                "id": str(uuid4()),
                "event_type": "created",
                "actor_name": actor.display_name,
                "actor_kind": "user",
                "message": payload.get("description") or "",
                "created_at": created_at,
            }
        ],
        "attachments": [],
    }
    _upsert_doc(actor, "case", case, case_id)
    return {"ok": True, "case": _case_enrich(actor, case)}


@router.post("/api/cases/search")
def cases_search(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _docs(session, "case", int(payload.get("limit") or 200))
    query = str(payload.get("q") or payload.get("query") or "").strip().lower()
    status_filter = str(payload.get("status") or "")
    type_filter = str(payload.get("type_key") or "")
    severity = str(payload.get("severity") or "")
    if query:
        rows = [
            row
            for row in rows
            if query in " ".join(
                str(row.get(key) or "").lower()
                for key in ("case_no", "title", "description", "location_text")
            )
        ]
    if status_filter:
        rows = [row for row in rows if str(row.get("status")) == status_filter]
    if type_filter:
        rows = [
            row
            for row in rows
            if str(row.get("type_key") or row.get("type_id")) == type_filter
        ]
    if severity:
        rows = [row for row in rows if str(row.get("severity")) == severity]
    if payload.get("mine"):
        rows = [
            row
            for row in rows
            if str(row.get("reporter_user_id")) == str(actor.user_id)
            or str(row.get("assignee_user_id")) == str(actor.user_id)
        ]
    enriched = [_case_enrich(actor, row) for row in rows]
    by_status = Counter(str(row.get("status") or "unknown") for row in enriched)
    completed = sum(1 for row in enriched if row.get("status") in {"resolved", "closed"})
    summary = {
        "total": len(enriched),
        "open": len(enriched) - completed,
        "completed": completed,
        "overdue": sum(1 for row in enriched if row.get("overdue")),
        "by_status": dict(by_status),
    }
    return {"cases": enriched, "items": enriched, "total": len(enriched), "summary": summary}


@router.get("/api/cases/analytics")
def cases_analytics(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _docs(session, "case", 1000)
    enriched = [_case_enrich(actor, row) for row in rows]
    by_status = Counter(str(row.get("status") or "unknown") for row in enriched)
    by_type = Counter(str(row.get("type_name_snapshot") or "通用事务") for row in enriched)
    by_department = Counter(str(row.get("owner_unit_name") or "未分配") for row in enriched)
    open_count = sum(1 for row in enriched if row.get("status") not in {"resolved", "closed", "cancelled"})
    return {
        "totals": {
            "total": len(enriched),
            "open": open_count,
            "overdue": sum(1 for row in enriched if row.get("overdue")),
            "avg_response_minutes": 0,
            "resolution_sla_hit_pct": 100 if enriched else 0,
        },
        "by_status": [{"key": key, "count": value} for key, value in sorted(by_status.items())],
        "by_type": [{"label": key, "count": value} for key, value in by_type.most_common()],
        "by_department": [
            {"label": key, "count": value} for key, value in by_department.most_common()
        ],
        "trend": [],
        "industry_metrics": [],
        "by_root_cause": [],
        "event_metrics": [],
    }


@router.get("/api/cases/{case_id}")
def cases_detail(
    case_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return {"case": _case_get(actor, case_id)}


@router.post("/api/cases/{case_id}/actions")
def cases_action(
    case_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    case = _case_get(actor, case_id)
    action = str(payload.get("action") or "").strip()
    transitions = {
        "submit": "submitted",
        "triage": "triaged",
        "assign": "assigned",
        "start": "in_progress",
        "resume": "in_progress",
        "wait": "waiting_external",
        "review": "pending_review",
        "resolve": "resolved",
        "close": "closed",
        "reopen": "in_progress",
        "cancel": "cancelled",
    }
    before = str(case.get("status") or "submitted")
    case["status"] = transitions.get(action, before)
    case["lock_version"] = int(case.get("lock_version") or 0) + 1
    case["updated_at"] = _iso_now()
    if action == "assign":
        assignee = payload.get("assignee_user_id")
        case["assignee_user_id"] = str(assignee) if assignee not in (None, "") else None
        case["assignee_name"] = str(payload.get("assignee_name") or assignee or "") or None
    for key in ("resolution_summary", "root_cause", "corrective_action", "satisfaction_rating"):
        if key in payload:
            case[key] = payload[key]
    if action == "resolve":
        case["resolved_at"] = _iso_now()
    if action == "close":
        case["closed_at"] = _iso_now()
    events = list(case.get("events") or [])
    events.append(
        {
            "id": str(uuid4()),
            "event_type": action or "updated",
            "actor_name": actor.display_name,
            "actor_kind": "user",
            "from_status": before,
            "to_status": case["status"],
            "message": str(payload.get("message") or ""),
            "created_at": _iso_now(),
        }
    )
    case["events"] = events
    case.pop("capabilities", None)
    case.pop("type_config", None)
    _upsert_doc(actor, "case", case, case_id)
    return {"ok": True, "case": _case_enrich(actor, case)}


@router.post("/api/cases/{case_id}/attachments")
async def case_attachment_upload(
    case_id: str,
    field_key: str = Form(default="attachment"),
    file: UploadFile = File(...),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    case = _case_get(actor, case_id)
    content = await file.read()
    blob = _blob_insert(
        actor,
        namespace="case.attachment",
        entity_key=case_id,
        field_key=field_key,
        file_name=file.filename or "attachment",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    attachment = {
        "id": blob["id"],
        "field_key": field_key,
        "file_name": blob["file_name"],
        "file_size": blob["file_size"],
        "content_type": blob["content_type"],
        "created_at": blob["created_at"],
    }
    case["attachments"] = [*(case.get("attachments") or []), attachment]
    case["lock_version"] = int(case.get("lock_version") or 0) + 1
    case["updated_at"] = _iso_now()
    case.pop("capabilities", None)
    case.pop("type_config", None)
    _upsert_doc(actor, "case", case, case_id)
    return {"ok": True, "attachment": attachment, "case": _case_enrich(actor, case)}


@router.get("/api/cases/{case_id}/attachments/{attachment_id}")
def case_attachment_download(
    case_id: str,
    attachment_id: str,
    actor: ActorContext = Depends(current_actor),
) -> Response:
    _ = case_id
    return _blob_response(actor, attachment_id)


@router.post("/api/cases/types")
def case_type_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    type_id = str(payload.get("id") or uuid4())
    item = {**payload, "id": type_id, "revision_no": 1, "active": payload.get("active", True)}
    _upsert_doc(actor, "case.type", item, type_id)
    types = _case_types(actor)
    return {"ok": True, "type": item, "types": types, "config_types": types}


@router.post("/api/cases/types/{type_id}")
def case_type_update(
    type_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    current = next((row for row in _case_types(actor) if str(row.get("id")) == type_id), {})
    item = {
        **current,
        **payload,
        "id": type_id,
        "revision_no": int(current.get("revision_no") or 0) + 1,
    }
    _upsert_doc(actor, "case.type", item, type_id)
    types = _case_types(actor)
    return {"ok": True, "type": item, "types": types, "config_types": types}


# ---------------------------------------------------------------------------
# Records


def _record_config_key(item: dict[str, object], *, kind: str) -> str:
    value = (
        item.get("key") or item.get("type_key") or item.get("id")
        if kind == "type"
        else item.get("key") or item.get("id")
    )
    return str(value or "").strip().lower()


def _record_config_defaults(
    rows: list[dict[str, object]], *, kind: str
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for source in rows:
        item = dict(source)
        key = _record_config_key(item, kind=kind)
        item.update(
            {
                "id": key,
                "key": key,
                "active": item.get("active", True),
                "revision_no": int(item.get("revision_no") or 1),
                "managed_by_template": True,
            }
        )
        if kind == "type":
            item["type_key"] = key
        result.append(item)
    return result


def _record_config_rows(actor: ActorContext, *, kind: str) -> list[dict[str, object]]:
    namespace = f"record.{kind}"
    defaults = _record_config_defaults(
        DEFAULT_RECORD_TYPES if kind == "type" else RECORD_CATEGORIES,
        kind=kind,
    )
    with tenant_session(actor.tenant_id) as session:
        stored = _docs(session, namespace, 500)
    merged = {_record_config_key(item, kind=kind): item for item in defaults}
    for source in stored:
        item = dict(source)
        key = _record_config_key(item, kind=kind)
        if not key:
            continue
        for metadata_key in ("document_key", "source", "version", "created_at", "updated_at"):
            item.pop(metadata_key, None)
        item.update(
            {
                "id": key,
                "key": key,
                "active": item.get("active", True),
                "revision_no": int(item.get("revision_no") or 1),
                "managed_by_template": bool(item.get("managed_by_template", False)),
            }
        )
        if kind == "type":
            item["type_key"] = key
        merged[key] = item
    return list(merged.values())


def _record_types(actor: ActorContext) -> list[dict[str, object]]:
    return sorted(
        _record_config_rows(actor, kind="type"),
        key=lambda item: (
            str(item.get("category_key") or ""),
            str(item.get("name") or ""),
        ),
    )


def _record_categories(actor: ActorContext) -> list[dict[str, object]]:
    return sorted(
        _record_config_rows(actor, kind="category"),
        key=lambda item: (
            int(item.get("order") or 0),
            str(item.get("name") or ""),
        ),
    )


def _can_configure_records(actor: ActorContext) -> bool:
    return actor.role_level >= 10 or bool(
        {"records.config.manage", "records.all.manage"} & actor.permissions
    )


def _require_record_configuration(actor: ActorContext) -> None:
    if not _can_configure_records(actor):
        raise HTTPException(status_code=403, detail="records.config.manage is required")


def _record_configuration(actor: ActorContext) -> dict[str, object]:
    categories = _record_categories(actor)
    types = _record_types(actor)
    revisions = [int(item.get("revision_no") or 1) for item in [*categories, *types]]
    return {
        "available": True,
        "can_configure": _can_configure_records(actor),
        "categories": categories,
        "types": types,
        "record_types": types,
        "template_revision": max(revisions or [1]),
    }


def _validated_record_config_payload(
    payload: dict[str, object], *, kind: str, expected_key: str | None = None
) -> tuple[str, dict[str, object]]:
    allowed = RECORD_TYPE_CONFIG_KEYS if kind == "type" else RECORD_CATEGORY_CONFIG_KEYS
    unknown = sorted(set(payload) - allowed - {"expected_revision_no"})
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported record configuration fields: {', '.join(unknown)}",
        )
    key = str(payload.get("key") or expected_key or "").strip().lower()
    if not RECORD_CONFIG_KEY_RE.fullmatch(key):
        raise HTTPException(status_code=422, detail="Invalid record configuration key")
    if expected_key is not None and key != expected_key:
        raise HTTPException(status_code=409, detail="Record configuration keys are immutable")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Record configuration name is required")
    result = {field: payload[field] for field in allowed if field in payload}
    result.update({"id": key, "key": key, "name": name})
    if kind == "type":
        category_key = str(result.get("category_key") or "").strip().lower()
        if not category_key:
            raise HTTPException(status_code=422, detail="Record type category is required")
        result.update({"type_key": key, "category_key": category_key})
    return key, result


def _store_record_config(
    actor: ActorContext,
    *,
    kind: str,
    key: str,
    item: dict[str, object],
    expected_revision_no: int | None,
    create: bool,
) -> dict[str, object]:
    namespace = f"record.{kind}"
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT payload, version
                    FROM compatibility.documents
                    WHERE namespace = :namespace AND document_key = :document_key
                    FOR UPDATE
                    """
                ),
                {"namespace": namespace, "document_key": key},
            )
            .mappings()
            .one_or_none()
        )
        if create and row is not None:
            raise HTTPException(status_code=409, detail="Record configuration already exists")
        current_revision = None
        if row is not None:
            current_payload = dict(row["payload"]) if isinstance(row["payload"], dict) else {}
            current_revision = int(current_payload.get("revision_no") or row["version"] or 1)
        if expected_revision_no is not None:
            current_revision = int(current_revision or 1)
            if expected_revision_no != current_revision:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "record_configuration_revision_conflict",
                        "expected_revision_no": expected_revision_no,
                        "current_revision_no": current_revision,
                    },
                )
        next_revision = 1 if create else int(current_revision or 1) + 1
        stored = {
            **item,
            "id": key,
            "key": key,
            "revision_no": next_revision,
            "managed_by_template": False,
        }
        if kind == "type":
            stored["type_key"] = key
        params = {
            "namespace": namespace,
            "document_key": key,
            "payload": json.dumps(stored, ensure_ascii=False, default=str),
            "updated_by": actor.user_id,
        }
        if row is None:
            inserted = session.execute(
                text(
                    """
                    INSERT INTO compatibility.documents(
                      id, tenant_id, namespace, document_key, payload, source, updated_by
                    ) VALUES (
                      :id, :tenant_id, :namespace, :document_key,
                      CAST(:payload AS jsonb), 'native', :updated_by
                    )
                    ON CONFLICT (tenant_id, namespace, document_key) DO NOTHING
                    RETURNING id
                    """
                ),
                {**params, "id": uuid4(), "tenant_id": actor.tenant_id},
            ).scalar_one_or_none()
            if inserted is None:
                raise HTTPException(status_code=409, detail="Record configuration already exists")
        else:
            session.execute(
                text(
                    """
                    UPDATE compatibility.documents
                    SET payload = CAST(:payload AS jsonb), status = 'active',
                        source = 'native', version = version + 1, updated_by = :updated_by
                    WHERE namespace = :namespace AND document_key = :document_key
                    """
                ),
                params,
            )
        _audit(
            session,
            actor,
            f"records.configuration.{('created' if create else 'revised')}",
            {"kind": kind, "key": key, "revision_no": next_revision},
        )
    return _safe(stored)


def _record_visible(actor: ActorContext, record: dict[str, object]) -> bool:
    if str(record.get("type_key") or "") != "personnel_record":
        return True
    subject_user_id = str(record.get("subject_user_id") or "")
    if subject_user_id and subject_user_id == str(actor.user_id):
        return True
    return actor.role_level >= 10 or bool(
        {"records.all.manage", "records.config.manage", "users.manage"} & actor.permissions
    )


def _record_get(actor: ActorContext, record_id: str) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = _doc(session, "record", record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Record not found")
    result = dict(row)
    if not _record_visible(actor, result):
        raise HTTPException(status_code=404, detail="Record not found")
    result.setdefault("id", record_id)
    result.setdefault("record_no", f"REC-{record_id[:8].upper()}")
    result.setdefault("lock_version", 1)
    result.setdefault("documents", [])
    result.setdefault("events", [])
    result.setdefault("relations", [])
    result.setdefault("capabilities", {"can_edit": True, "available_actions": ["submit", "archive", "reopen"]})
    return _safe(result)


@router.get("/api/records/meta")
def records_meta_full(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    units, users = _tenant_people(actor)
    configuration = _record_configuration(actor)
    types = configuration["types"]
    can_configure = _can_configure_records(actor)
    can_create = actor.role_level >= 10 or bool(
        {"records.create", "records.all.manage"} & actor.permissions
    )
    return {
        "available": True,
        "types": types,
        "record_types": types,
        "categories": configuration["categories"],
        "confidentialities": [
            {"value": "internal", "label": "内部"},
            {"value": "sensitive", "label": "敏感"},
            {"value": "restricted", "label": "受限"},
        ],
        "units": units,
        "users": users,
        "can_create": can_create,
        "can_configure": can_configure,
        "permissions": {"can_create": can_create, "can_configure": can_configure},
        "template_revision": configuration["template_revision"],
    }


@router.get("/api/records/config")
def records_configuration_get(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_record_configuration(actor)
    return _record_configuration(actor)


def _record_config_create(
    actor: ActorContext, payload: dict[str, object], *, kind: str
) -> dict[str, object]:
    _require_record_configuration(actor)
    key, item = _validated_record_config_payload(payload, kind=kind)
    catalog = _record_types(actor) if kind == "type" else _record_categories(actor)
    if any(_record_config_key(row, kind=kind) == key for row in catalog):
        raise HTTPException(status_code=409, detail="Record configuration already exists")
    if kind == "type":
        categories = {str(row.get("key")): row for row in _record_categories(actor)}
        category = categories.get(str(item.get("category_key")))
        if category is None or category.get("active") is False:
            raise HTTPException(status_code=422, detail="Record type category is not active")
    stored = _store_record_config(
        actor,
        kind=kind,
        key=key,
        item={**item, "active": True},
        expected_revision_no=None,
        create=True,
    )
    return {"ok": True, kind: stored, **_record_configuration(actor)}


@router.post("/api/records/config/categories", status_code=201)
def records_category_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _record_config_create(actor, payload, kind="category")


@router.post("/api/records/config/types", status_code=201)
def records_type_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _record_config_create(actor, payload, kind="type")


def _record_config_revise(
    actor: ActorContext,
    payload: dict[str, object],
    *,
    kind: str,
    key: str,
) -> dict[str, object]:
    _require_record_configuration(actor)
    clean_key = key.strip().lower()
    catalog = _record_types(actor) if kind == "type" else _record_categories(actor)
    current = next(
        (row for row in catalog if _record_config_key(row, kind=kind) == clean_key),
        None,
    )
    if current is None:
        raise HTTPException(status_code=404, detail="Record configuration not found")
    try:
        expected_revision = int(payload.get("expected_revision_no") or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="expected_revision_no is required") from exc
    if expected_revision < 1:
        raise HTTPException(status_code=422, detail="expected_revision_no is required")
    _, update = _validated_record_config_payload(
        payload, kind=kind, expected_key=clean_key
    )
    if kind == "type":
        categories = {str(row.get("key")): row for row in _record_categories(actor)}
        category = categories.get(str(update.get("category_key")))
        if category is None or category.get("active") is False:
            raise HTTPException(status_code=422, detail="Record type category is not active")
    stored = _store_record_config(
        actor,
        kind=kind,
        key=clean_key,
        item={**current, **update, "active": current.get("active", True)},
        expected_revision_no=expected_revision,
        create=False,
    )
    return {"ok": True, kind: stored, **_record_configuration(actor)}


@router.post("/api/records/config/categories/{category_key}/revisions")
def records_category_revise(
    category_key: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _record_config_revise(actor, payload, kind="category", key=category_key)


@router.post("/api/records/config/types/{type_key}/revisions")
def records_type_revise(
    type_key: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _record_config_revise(actor, payload, kind="type", key=type_key)


def _record_config_disable(
    actor: ActorContext, *, kind: str, key: str, expected: object
) -> dict[str, object]:
    _require_record_configuration(actor)
    clean_key = key.strip().lower()
    catalog = _record_types(actor) if kind == "type" else _record_categories(actor)
    current = next(
        (row for row in catalog if _record_config_key(row, kind=kind) == clean_key),
        None,
    )
    if current is None:
        raise HTTPException(status_code=404, detail="Record configuration not found")
    try:
        expected_revision = int(expected or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="expected_revision_no is required") from exc
    if expected_revision < 1:
        raise HTTPException(status_code=422, detail="expected_revision_no is required")
    if kind == "category" and any(
        row.get("active") is not False and str(row.get("category_key")) == clean_key
        for row in _record_types(actor)
    ):
        raise HTTPException(
            status_code=409,
            detail="Disable or move active record types before disabling this category",
        )
    stored = _store_record_config(
        actor,
        kind=kind,
        key=clean_key,
        item={**current, "active": False},
        expected_revision_no=expected_revision,
        create=False,
    )
    return {"ok": True, kind: stored, **_record_configuration(actor)}


@router.post("/api/records/config/categories/{category_key}/disable")
def records_category_disable(
    category_key: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _record_config_disable(
        actor,
        kind="category",
        key=category_key,
        expected=payload.get("expected_revision_no"),
    )


@router.post("/api/records/config/types/{type_key}/disable")
def records_type_disable(
    type_key: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _record_config_disable(
        actor,
        kind="type",
        key=type_key,
        expected=payload.get("expected_revision_no"),
    )


@router.post("/api/records", status_code=201)
def records_create_full(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    record_id = str(uuid4())
    created_at = _iso_now()
    record = {
        "id": record_id,
        "record_no": f"REC-{datetime.now(UTC):%Y%m%d}-{record_id[:8].upper()}",
        "type_id": payload.get("type_id"),
        "type_key": payload.get("type_key") or "general_record",
        "category_key": payload.get("category_key") or "other",
        "category_name_snapshot": payload.get("category_key") or "其他档案",
        "title": str(payload.get("title") or "Untitled record")[:240],
        "description": str(payload.get("description") or ""),
        "status": str(payload.get("status") or "draft"),
        "confidentiality": str(payload.get("confidentiality") or "internal"),
        "effective_at": payload.get("effective_at"),
        "expires_at": payload.get("expires_at"),
        "fields": payload.get("fields") if isinstance(payload.get("fields"), dict) else {},
        "created_by": str(actor.user_id),
        "created_by_name": actor.display_name,
        "created_at": created_at,
        "updated_at": created_at,
        "lock_version": 1,
        "documents": [],
        "events": [
            {
                "id": str(uuid4()),
                "event_type": "created",
                "actor_name": actor.display_name,
                "message": "",
                "created_at": created_at,
            }
        ],
        "relations": [],
    }
    _upsert_doc(actor, "record", record, record_id)
    return {"ok": True, "record": _record_get(actor, record_id)}


@router.post("/api/records/search")
def records_search_full(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _docs(session, "record", int(payload.get("limit") or 200))
    query = str(payload.get("query") or payload.get("q") or "").strip().lower()
    if query:
        rows = [
            row
            for row in rows
            if query in " ".join(
                str(row.get(key) or "").lower()
                for key in ("record_no", "title", "description")
            )
        ]
    rows = [row for row in rows if _record_visible(actor, row)]
    for source, key in (("status", "status"), ("type", "type_key"), ("record_type", "type_key"), ("category", "category_key")):
        value = str(payload.get(source) or "")
        if value:
            rows = [row for row in rows if str(row.get(key)) == value]
    records = [_record_get(actor, str(row.get("document_key") or row.get("id"))) for row in rows]
    return {
        "available": True,
        "records": records,
        "items": records,
        "total": len(records),
        "count": len(records),
        "summary": {
            "total": len(records),
            "by_status": dict(Counter(str(row.get("status") or "unknown") for row in records)),
        },
    }


@router.get("/api/records/{record_id}")
def records_detail(
    record_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return {"record": _record_get(actor, record_id)}


@router.post("/api/records/{record_id}/actions")
def records_action(
    record_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    record = _record_get(actor, record_id)
    action = str(payload.get("action") or "updated")
    transitions = {
        "submit": "pending_review",
        "approve": "active",
        "archive": "archived",
        "reopen": "active",
        "hold": "legal_hold",
        "destroy": "destroyed",
    }
    before = str(record.get("status") or "draft")
    record["status"] = transitions.get(action, before)
    record["lock_version"] = int(record.get("lock_version") or 0) + 1
    record["updated_at"] = _iso_now()
    record["events"] = [
        *(record.get("events") or []),
        {
            "id": str(uuid4()),
            "event_type": action,
            "actor_name": actor.display_name,
            "from_status": before,
            "to_status": record["status"],
            "message": str(payload.get("message") or ""),
            "created_at": _iso_now(),
        },
    ]
    record.pop("capabilities", None)
    _upsert_doc(actor, "record", record, record_id)
    return {"ok": True, "record": _record_get(actor, record_id)}


@router.post("/api/records/{record_id}/documents")
async def record_document_upload(
    record_id: str,
    file: UploadFile = File(...),
    field_key: str = Form(default="document"),
    title: str = Form(default=""),
    visibility: str = Form(default="record"),
    document_id: str | None = Form(default=None),
    lock_version: int | None = Form(default=None),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _ = (document_id, lock_version)
    record = _record_get(actor, record_id)
    content = await file.read()
    blob = _blob_insert(
        actor,
        namespace="record.document",
        entity_key=record_id,
        field_key=field_key,
        file_name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        metadata={"title": title, "visibility": visibility},
    )
    version = {
        "id": blob["id"],
        "version_id": blob["id"],
        "field_key": field_key,
        "title": title or blob["file_name"],
        "file_name": blob["file_name"],
        "file_size": blob["file_size"],
        "content_type": blob["content_type"],
        "created_at": blob["created_at"],
        "download_url": f"/api/records/{record_id}/documents/{blob['id']}/download",
    }
    record["documents"] = [
        *(record.get("documents") or []),
        {"id": blob["id"], "title": title or blob["file_name"], "versions": [version]},
    ]
    record["lock_version"] = int(record.get("lock_version") or 0) + 1
    record["updated_at"] = _iso_now()
    record.pop("capabilities", None)
    _upsert_doc(actor, "record", record, record_id)
    return {"ok": True, "version": version, "record": _record_get(actor, record_id)}


@router.get("/api/records/{record_id}/documents/{blob_id}/download")
@router.get("/api/records/{record_id}/documents/{blob_id}")
def record_document_download(
    record_id: str,
    blob_id: str,
    actor: ActorContext = Depends(current_actor),
) -> Response:
    _ = record_id
    return _blob_response(actor, blob_id)


@router.get("/api/records/documents/{blob_id}/download")
def record_document_download_alias(
    blob_id: str,
    actor: ActorContext = Depends(current_actor),
) -> Response:
    return _blob_response(actor, blob_id)


# ---------------------------------------------------------------------------
# Workflow compatibility


def _workflow_definition(actor: ActorContext, workflow_key: str) -> dict[str, object] | None:
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                SELECT id, workflow_key, name, version, definition, active,
                       created_at, updated_at
                FROM workflow.definitions
                WHERE workflow_key = :key AND active
                ORDER BY version DESC LIMIT 1
                """
            ),
            {"key": workflow_key},
        ).mappings().one_or_none()
    return _safe(dict(row)) if row else None


def _workflow_node_view(source: object) -> dict[str, object]:
    """Project versioned workflow JSON into the stable frontend/AI map shape."""

    node = dict(source) if isinstance(source, dict) else {}
    node.setdefault("node_kind", node.get("kind"))
    node.setdefault("artifactKinds", node.get("artifact_kinds") or [])
    sla = node.get("sla")
    if isinstance(sla, dict):
        node.setdefault("sla_hours", sla.get("default_hours"))
    quorum = node.get("quorum")
    if isinstance(quorum, dict):
        node["quorum"] = quorum.get("default", 1)
    assignment = node.get("assignment")
    if isinstance(assignment, dict):
        strategy = str(assignment.get("strategy") or "")
        node.setdefault("position_binding_mode", strategy)
        node.setdefault("assignee_department_code", assignment.get("department_code"))
        node.setdefault("assignee_position_code", assignment.get("position_code"))
        rule_by_strategy = {
            "initiator": "initiator",
            "context_department_manager": "dept_manager",
            "external_party": "external_party",
            "gateway": "gateway",
            "responsibility_slot": "role",
        }
        node.setdefault("assign_rule", rule_by_strategy.get(strategy, strategy))
        if strategy == "responsibility_slot":
            node.setdefault("assign_value", assignment.get("responsibility"))
    gateway = node.get("gateway")
    if isinstance(gateway, dict) and not isinstance(node.get("branches"), dict):
        branches = dict(gateway)
        if isinstance(gateway.get("branches"), list):
            branches["branches"] = [
                {
                    **branch,
                    "cond": {
                        "field": condition.get("field"),
                        "op": condition.get("operator") or condition.get("op"),
                        "value": (
                            condition.get("value")
                            if condition.get("value") is not None
                            else condition.get("parameter_ref")
                        ),
                    }
                    if isinstance((condition := branch.get("condition")), dict)
                    else None,
                }
                for branch in gateway["branches"]
                if isinstance(branch, dict)
            ]
        node["branches"] = branches
    return node


@router.get("/api/wf/workflows/{workflow_key}/map")
def workflow_map(
    workflow_key: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    definition = _workflow_definition(actor, workflow_key)
    if definition is None:
        with tenant_session(actor.tenant_id) as session:
            stored = _doc(session, "workflow.node_config", workflow_key) or {}
        return {"workflow_key": workflow_key, "nodes": stored.get("nodes", []), "edges": []}
    body = definition.get("definition") if isinstance(definition.get("definition"), dict) else {}
    nodes = [
        _workflow_node_view(node)
        for node in (body.get("nodes") if isinstance(body.get("nodes"), list) else [])
    ]
    return {
        "workflow_key": workflow_key,
        "workflow": definition,
        "command_binding_schema_version": body.get(
            "command_binding_schema_version"
        ),
        "stages": body.get("stages", []),
        "nodes": nodes,
        "edges": body.get("edges", []),
        "command_action_count": sum(
            len(node.get("actions") or [])
            for node in nodes
            if isinstance(node, dict)
        ),
    }


@router.get("/api/wf/workflows/{workflow_key}/nodes")
def workflow_nodes(
    workflow_key: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        stored = _doc(session, "workflow.node_config", workflow_key)
    definition = _workflow_definition(actor, workflow_key)
    if stored:
        return {
            "workflow_key": workflow_key,
            "definition": {"base_version": stored.get("base_version", 1)},
            "workflow": definition or {"workflow_key": workflow_key, "version": stored.get("base_version", 1)},
            "nodes": stored.get("nodes", []),
        }
    body = definition.get("definition") if definition and isinstance(definition.get("definition"), dict) else {}
    return {
        "workflow_key": workflow_key,
        "definition": {"base_version": definition.get("version", 1) if definition else 1},
        "workflow": definition or {"workflow_key": workflow_key, "version": 1},
        "nodes": body.get("nodes", []),
    }


@router.post("/api/wf/workflows/{workflow_key}/nodes")
def workflow_nodes_save(
    workflow_key: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    state = {
        "workflow_key": workflow_key,
        "nodes": payload.get("nodes") if isinstance(payload.get("nodes"), list) else [],
        "base_version": int(payload.get("base_version") or 1),
        "updated_at": _iso_now(),
    }
    _upsert_doc(actor, "workflow.node_config", state, workflow_key)
    return {"ok": True, **state}


@router.get("/api/wf/repairs")
def workflow_repairs(
    limit: int = Query(default=50, ge=1, le=500),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _docs(session, "workflow.repair", limit)
    return {"available": True, "repairs": rows, "cases": rows, "items": rows}


@router.post("/api/wf/instances/{instance_id}/repair-scan")
def workflow_repair_scan(
    instance_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    repair_id = str(uuid4())
    item = {
        "id": repair_id,
        "case_id": repair_id,
        "instance_id": instance_id,
        "status": "open",
        "reason": payload.get("reason") or "manual_scan",
        "findings": [],
        "created_at": _iso_now(),
        "updated_at": _iso_now(),
    }
    _upsert_doc(actor, "workflow.repair", item, repair_id)
    return {"ok": True, "repair": item, "case": item, **item}


@router.get("/api/wf/instances/{instance_id}")
def workflow_instance_detail(
    instance_id: UUID,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                SELECT wi.*, wd.workflow_key, wd.name AS workflow_name, wd.definition
                FROM workflow.instances wi
                JOIN workflow.definitions wd
                  ON wd.tenant_id = wi.tenant_id AND wd.id = wi.definition_id
                WHERE wi.id = :id
                """
            ),
            {"id": instance_id},
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        attachment_rows = session.execute(
            text(
                """
                SELECT attachment.*, user_account.display_name AS uploaded_by_name
                FROM workflow.node_attachments AS attachment
                LEFT JOIN iam.users AS user_account
                  ON user_account.id = attachment.uploaded_by
                WHERE attachment.instance_id = :instance_id
                ORDER BY attachment.created_at DESC, attachment.id DESC
                """
            ),
            {"instance_id": instance_id},
        ).mappings().all()
    return {
        "instance": _safe(dict(row)),
        "timeline": [],
        "artifacts": [
            _workflow_attachment_public(dict(attachment)) for attachment in attachment_rows
        ],
    }


@router.get("/api/wf/instances/{instance_id}/nodes/{node_key}/attachments")
def workflow_node_attachment_list(
    instance_id: UUID,
    node_key: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        instance_exists = session.execute(
            text("SELECT 1 FROM workflow.instances WHERE id = :instance_id"),
            {"instance_id": instance_id},
        ).scalar_one_or_none()
        if instance_exists is None:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        rows = session.execute(
            text(
                """
                SELECT attachment.*, user_account.display_name AS uploaded_by_name
                FROM workflow.node_attachments AS attachment
                LEFT JOIN iam.users AS user_account
                  ON user_account.id = attachment.uploaded_by
                WHERE attachment.instance_id = :instance_id
                  AND attachment.node_key = :node_key
                ORDER BY attachment.created_at DESC, attachment.id DESC
                """
            ),
            {"instance_id": instance_id, "node_key": node_key},
        ).mappings().all()
    attachments = [_workflow_attachment_public(dict(row)) for row in rows]
    return {
        "available": True,
        "instance_id": str(instance_id),
        "node_key": node_key,
        "attachments": attachments,
        "items": attachments,
        "count": len(attachments),
    }


@router.post("/api/wf/instances/{instance_id}/nodes/{node_key}/attachments")
async def workflow_node_attachment_upload(
    instance_id: UUID,
    node_key: str,
    file: UploadFile = File(...),
    kind: str = Form(default="node_attachment"),
    expected_sha256: str | None = Form(default=None),
    attachment_key: str | None = Form(default=None),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    content = await file.read(settings.workflow_attachment_max_upload_bytes + 1)
    file_name, content_type = _workflow_attachment_file(file, content, settings)
    logical_key: UUID | None = None
    if attachment_key:
        try:
            logical_key = UUID(attachment_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid attachment key") from exc
    attachment = _store_workflow_node_attachment(
        actor,
        settings,
        instance_id=instance_id,
        node_key=node_key,
        kind=kind,
        file_name=file_name,
        content_type=content_type,
        content=content,
        expected_sha256=expected_sha256,
        attachment_key=logical_key,
    )
    return {
        "ok": True,
        "attachment": attachment,
        "artifact": attachment,
        "notary": {
            "serial": attachment["notary_serial"],
            "content_sha256": attachment["content_sha256"],
            "event_hash": attachment["event_hash"],
            "signature": attachment["notary_signature"],
        },
    }


@router.post("/api/wf/tasks/{task_id}/artifact/upload")
async def workflow_artifact_upload(
    task_id: str,
    kind: str = Form(default="attachment"),
    file: UploadFile = File(...),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    content = await file.read(settings.workflow_attachment_max_upload_bytes + 1)
    file_name, content_type = _workflow_attachment_file(file, content, settings)
    with tenant_session(actor.tenant_id) as session:
        task_rows = _docs(session, "workflow.inbox", 1000)
    task = next(
        (
            row
            for row in task_rows
            if str(row.get("id") or row.get("document_key")) == task_id
        ),
        None,
    )
    task_instance_id = (task or {}).get("instance_id")
    task_node_key = (task or {}).get("node_key")
    if task_instance_id and task_node_key:
        try:
            instance_uuid = UUID(str(task_instance_id))
        except ValueError:
            instance_uuid = None
        if instance_uuid is not None:
            attachment = _store_workflow_node_attachment(
                actor,
                settings,
                instance_id=instance_uuid,
                node_key=str(task_node_key),
                kind=kind,
                file_name=file_name,
                content_type=content_type,
                content=content,
            )
            return {"ok": True, "artifact": attachment, "attachment": attachment}

    content_sha256 = hashlib.sha256(content).hexdigest()
    blob = _blob_insert(
        actor,
        namespace="workflow.artifact",
        entity_key=task_id,
        field_key=kind,
        file_name=file_name,
        content_type=content_type,
        content=content,
        metadata={"kind": kind, "content_sha256": content_sha256},
    )
    artifact = {
        "id": blob["id"],
        "task_id": task_id,
        "kind": kind,
        "file_name": blob["file_name"],
        "file_size": blob["file_size"],
        "created_at": blob["created_at"],
        "version": 1,
        "file_sha256": content_sha256,
        "has_file": True,
    }
    return {"ok": True, "artifact": artifact}


@router.get("/api/wf/artifacts/{artifact_id}/download")
def workflow_artifact_download(
    artifact_id: UUID,
    actor: ActorContext = Depends(current_actor),
) -> Response:
    with tenant_session(actor.tenant_id) as session:
        blob_id = session.execute(
            text(
                """
                SELECT blob_id
                FROM workflow.node_attachments
                WHERE id = :attachment_id
                """
            ),
            {"attachment_id": artifact_id},
        ).scalar_one_or_none()
    return _blob_response(actor, str(blob_id or artifact_id))


@router.get("/api/wf/node-attachments/{attachment_id}/verify")
def workflow_node_attachment_verify(
    attachment_id: UUID,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                SELECT attachment.*, blob.content
                FROM workflow.node_attachments AS attachment
                JOIN compatibility.blobs AS blob
                  ON blob.tenant_id = attachment.tenant_id
                 AND blob.id = attachment.blob_id
                WHERE attachment.id = :attachment_id
                """
            ),
            {"attachment_id": attachment_id},
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Workflow attachment not found")
        previous_event_hash = None
        if int(row["version"]) > 1:
            previous_event_hash = session.execute(
                text(
                    """
                    SELECT event_hash
                    FROM workflow.node_attachments
                    WHERE instance_id = :instance_id
                      AND node_key = :node_key
                      AND attachment_key = :attachment_key
                      AND version = :previous_version
                    """
                ),
                {
                    "instance_id": row["instance_id"],
                    "node_key": row["node_key"],
                    "attachment_key": row["attachment_key"],
                    "previous_version": int(row["version"]) - 1,
                },
            ).scalar_one_or_none()

    verification_row = dict(row)
    content_sha256 = hashlib.sha256(bytes(verification_row.pop("content"))).hexdigest()
    event_hash = hashlib.sha256(_workflow_attachment_material(verification_row)).hexdigest()
    signature = hmac.new(
        settings.integration_secret.encode("utf-8"),
        event_hash.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    checks = {
        "content": hmac.compare_digest(content_sha256, str(row["content_sha256"])),
        "event": hmac.compare_digest(event_hash, str(row["event_hash"])),
        "signature": hmac.compare_digest(signature, str(row["notary_signature"])),
        "chain": (
            row["previous_event_hash"] is None
            if int(row["version"]) == 1
            else previous_event_hash is not None
            and hmac.compare_digest(
                str(previous_event_hash), str(row["previous_event_hash"])
            )
        ),
    }
    verified = all(checks.values())
    return {
        "ok": verified,
        "verified": verified,
        "status": "verified" if verified else "tampered",
        "attachment_id": str(attachment_id),
        "notary_serial": row["notary_serial"],
        "content_sha256": content_sha256,
        "event_hash": event_hash,
        "checks": checks,
        "verified_at": _iso_now(),
    }


@router.post("/api/wf/tasks/{task_id}/{action}")
def workflow_task_action(
    task_id: str,
    action: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _docs(session, "workflow.inbox", 1000)
    current = next((row for row in rows if str(row.get("id") or row.get("document_key")) == task_id), {})
    item = {
        **current,
        "id": task_id,
        "status": "completed" if action in {"approve", "submit", "complete"} else ("rejected" if action == "reject" else action),
        "last_action": action,
        "comment": payload.get("comment") or payload.get("message") or "",
        "updated_at": _iso_now(),
    }
    _upsert_doc(actor, "workflow.inbox", item, task_id)
    return {"ok": True, "task": item, "action": action}


# ---------------------------------------------------------------------------
# Remaining operational endpoints used by retained pages.


@router.post("/api/cli/attachments")
def cli_attachment(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    attachment_id = str(uuid4())
    item = {
        "id": attachment_id,
        "name": payload.get("name") or payload.get("file_name") or "attachment",
        "content": payload.get("content") or payload.get("data") or "",
        "content_type": payload.get("content_type") or "text/plain",
        "created_at": _iso_now(),
    }
    _upsert_doc(actor, "cli.attachment", item, attachment_id)
    return {"ok": True, "attachment": item}


@router.post("/api/legal/contracts/{contract_id}/sign")
def legal_contract_sign(
    contract_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    item = {
        "id": contract_id,
        "status": "signed",
        "signed_by": str(actor.user_id),
        "signed_by_name": actor.display_name,
        "signed_at": _iso_now(),
        "payload": payload,
    }
    _upsert_doc(actor, "legal.contract", item, contract_id)
    return {"ok": True, "contract": item}


@router.post("/api/legal/seals/{seal_id}/stamp")
def legal_seal_stamp(
    seal_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    item = {
        "id": seal_id,
        "status": "stamped",
        "stamped_by": str(actor.user_id),
        "stamped_by_name": actor.display_name,
        "stamped_at": _iso_now(),
        "payload": payload,
    }
    _upsert_doc(actor, "legal.seal", item, seal_id)
    return {"ok": True, "seal": item}
