# ruff: noqa: E501
"""Functional PostgreSQL compatibility for retained business pages."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.api.full_stack_identity import _audit, _doc, _docs, _safe, _upsert_doc
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
        "fields": [],
    },
]

RECORD_CATEGORIES = [
    {"key": "personnel", "name": "人员档案", "icon": "user"},
    {"key": "meeting", "name": "会议档案", "icon": "clipboard"},
    {"key": "training", "name": "培训档案", "icon": "doc"},
    {"key": "safety", "name": "安全档案", "icon": "shield"},
    {"key": "case", "name": "事务档案", "icon": "layers"},
    {"key": "other", "name": "其他档案", "icon": "box"},
]


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
    return Response(
        content=bytes(row["content"]),
        media_type=row["content_type"],
        headers={"Content-Disposition": f'attachment; filename="{row["file_name"]}"'},
    )


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


def _record_types(actor: ActorContext) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = _docs(session, "record.type", 500)
    return rows or [dict(row) for row in DEFAULT_RECORD_TYPES]


def _record_get(actor: ActorContext, record_id: str) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = _doc(session, "record", record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Record not found")
    result = dict(row)
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
    types = _record_types(actor)
    return {
        "available": True,
        "types": types,
        "record_types": types,
        "categories": RECORD_CATEGORIES,
        "confidentialities": [
            {"value": "internal", "label": "内部"},
            {"value": "sensitive", "label": "敏感"},
            {"value": "restricted", "label": "受限"},
        ],
        "units": units,
        "users": users,
        "permissions": {"can_create": True, "can_configure": True},
    }


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
    return {
        "workflow_key": workflow_key,
        "workflow": definition,
        "nodes": body.get("nodes", []),
        "edges": body.get("edges", []),
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
    instance_id: str,
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
            {"id": UUID(instance_id)},
        ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    return {"instance": _safe(dict(row)), "timeline": [], "artifacts": []}


@router.post("/api/wf/tasks/{task_id}/artifact/upload")
async def workflow_artifact_upload(
    task_id: str,
    kind: str = Form(default="attachment"),
    file: UploadFile = File(...),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    content = await file.read()
    blob = _blob_insert(
        actor,
        namespace="workflow.artifact",
        entity_key=task_id,
        field_key=kind,
        file_name=file.filename or "artifact",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        metadata={"kind": kind},
    )
    artifact = {
        "id": blob["id"],
        "task_id": task_id,
        "kind": kind,
        "file_name": blob["file_name"],
        "file_size": blob["file_size"],
        "created_at": blob["created_at"],
        "version": 1,
    }
    return {"ok": True, "artifact": artifact}


@router.get("/api/wf/artifacts/{artifact_id}/download")
def workflow_artifact_download(
    artifact_id: str,
    actor: ActorContext = Depends(current_actor),
) -> Response:
    return _blob_response(actor, artifact_id)


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


@router.get("/api/shield/status")
def shield_status(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        state = _doc(session, "shield.status") or {}
    result = {
        "status": "ready",
        "database": "connected",
        "frontend": "connected",
        "backend": "connected",
        "last_repair_at": None,
        **state,
    }
    return {"available": True, **_safe(result)}


@router.post("/api/shield/repair")
def shield_repair(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    state = {
        "status": "ready",
        "last_repair_at": _iso_now(),
        "last_action": payload.get("action") or "repair",
        "result": "completed",
    }
    _upsert_doc(actor, "shield.status", state)
    return {"ok": True, **state}


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
