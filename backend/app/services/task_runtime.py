"""Typed Auto Runtime adapter for the native task centre.

The task API remains the only business mutation boundary.  This module gives
the shared command runtime a domain adapter that can resolve optimistic
versions, retry safe field/status changes once, and emit a deterministic
read-after-write observation for the reflection ledger.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder

from app.services import task_center

if TYPE_CHECKING:
    from app.api.deps import ActorContext


TASK_RUNTIME_TOOLS = frozenset(
    {
        "task_meta",
        "task_list",
        "task_resolve",
        "task_show",
        "task_history",
        "task_create",
        "task_update",
        "task_status",
        "task_delete",
    }
)

_DATETIME_FIELDS = frozenset({"start_at", "end_at", "due_at"})
_VERIFY_EXCLUDED_FIELDS = frozenset({"client_request_id", "expected_version", "confirm", "note"})


def _body(values: Mapping[str, object]) -> dict[str, object]:
    return {
        key.removeprefix("body."): value
        for key, value in values.items()
        if key.startswith("body.") and value is not None
    }


def _path(values: Mapping[str, object], name: str) -> str:
    value = str(values.get(f"path.{name}") or "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing task {name}",
        )
    return value


def _integer(value: object, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid numeric task filter") from exc
    return min(maximum, max(minimum, parsed))


def _datetime(value: object | None, *, label: str) -> datetime | None:
    if value in (None, ""):
        return None
    candidate = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {label}") from exc


def _same_datetime(left: object, right: object) -> bool:
    try:
        left_time = _datetime(left, label="expected task time")
        right_time = _datetime(right, label="observed task time")
    except HTTPException:
        return str(left) == str(right)
    if left_time is None or right_time is None:
        return left_time is right_time
    if left_time.tzinfo is None or right_time.tzinfo is None:
        return left_time.replace(tzinfo=None) == right_time.replace(tzinfo=None)
    return left_time.timestamp() == right_time.timestamp()


def _same_field(field: str, expected: object, observed: object) -> bool:
    if field in _DATETIME_FIELDS:
        return _same_datetime(expected, observed)
    if field == "assignees":
        expected_ids = {str(item) for item in (expected or [])}
        observed_ids = {
            str(item.get("id") or item.get("user_id"))
            for item in (observed or [])
            if isinstance(item, dict)
        }
        return expected_ids == observed_ids
    if expected in (None, "") and observed in (None, ""):
        return True
    if isinstance(expected, bool):
        return observed is expected
    return str(expected) == str(observed)


def _verified_fields(
    intended: Mapping[str, object], observed: Mapping[str, object]
) -> tuple[list[str], list[str]]:
    matched: list[str] = []
    mismatched: list[str] = []
    for field, expected in intended.items():
        if field in _VERIFY_EXCLUDED_FIELDS:
            continue
        target = matched if _same_field(field, expected, observed.get(field)) else mismatched
        target.append(field)
    return sorted(matched), sorted(mismatched)


def _observation(
    *,
    operation: str,
    state: str,
    origin: str,
    task: Mapping[str, object] | None = None,
    count: int | None = None,
    verified_fields: list[str] | None = None,
    mismatched_fields: list[str] | None = None,
    conflict_retries: int = 0,
) -> dict[str, object]:
    task = task or {}
    return {
        "schema": "warehouse.world-observation.v1",
        "decision_owner": "auto_runtime",
        "semantic_resource": "workflow.task",
        "operation": operation,
        "state": state,
        "origin": origin,
        "canonical_entity": (
            {
                "task_id": task.get("id"),
                "version": task.get("version"),
            }
            if task.get("id")
            else None
        ),
        "observed": {
            key: task.get(key)
            for key in (
                "title",
                "kind",
                "category",
                "status",
                "priority",
                "start_at",
                "end_at",
                "due_at",
                "all_day",
                "plan_id",
            )
            if key in task
        },
        "count": count,
        "verified_fields": verified_fields or [],
        "mismatched_fields": mismatched_fields or [],
        "conflict_retries": conflict_retries,
    }


def _task_result(
    task: Mapping[str, object],
    *,
    operation: str,
    intended: Mapping[str, object],
    origin: str,
    conflict_retries: int = 0,
) -> dict[str, object]:
    observed = dict(jsonable_encoder(dict(task)))
    matched, mismatched = _verified_fields(intended, observed)
    state = "verified" if not mismatched else "verification_mismatch"
    verification = {
        "state": state,
        "semantic_resource": "workflow.task",
        "task_id": observed.get("id"),
        "version": observed.get("version"),
        "verified_fields": matched,
        "mismatched_fields": mismatched,
        "conflict_retries": conflict_retries,
    }
    return {
        **observed,
        "verification": verification,
        "world_observation": _observation(
            operation=operation,
            state=state,
            origin=origin,
            task=observed,
            verified_fields=matched,
            mismatched_fields=mismatched,
            conflict_retries=conflict_retries,
        ),
    }


def _safe_versioned_write(
    actor: ActorContext,
    task_id: str,
    payload: dict[str, object],
    operation: str,
) -> tuple[dict[str, object], int]:
    current = task_center.get_task(actor, task_id)
    retries = 0
    if payload.get("expected_version") != current.get("version"):
        payload["expected_version"] = current["version"]
        retries += 1
    writer = task_center.update_task_status if operation == "status" else task_center.update_task
    try:
        writer(actor, task_id, payload)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_409_CONFLICT:
            raise
        latest = task_center.get_task(actor, task_id)
        payload["expected_version"] = latest["version"]
        retries += 1
        writer(actor, task_id, payload)
    return task_center.get_task(actor, task_id), retries


def _filtered_task_list(
    actor: ActorContext, values: Mapping[str, object], origin: str
) -> dict[str, object]:
    scope = str(values.get("query.scope") or "mine")
    payload = task_center.list_tasks(actor, scope=scope)
    items = [dict(jsonable_encoder(item)) for item in payload.get("items") or []]
    status_filter = str(values.get("query.status") or "").strip()
    source_filter = str(values.get("query.source_type") or "").strip()
    query = str(values.get("query.q") or "").strip().casefold()
    from_time = _datetime(values.get("query.from"), label="task range start")
    to_time = _datetime(values.get("query.to"), label="task range end")

    def visible(item: Mapping[str, object]) -> bool:
        if status_filter and item.get("status") != status_filter:
            return False
        if source_filter and item.get("source_type") != source_filter:
            return False
        if query:
            haystack = " ".join(
                str(item.get(key) or "")
                for key in ("id", "title", "description", "source_entity_id")
            ).casefold()
            if query not in haystack:
                return False
        if from_time is None and to_time is None:
            return True
        moment = _datetime(
            item.get("due_at") or item.get("start_at") or item.get("end_at"),
            label="observed task time",
        )
        if moment is None:
            return False
        if from_time is not None and moment.timestamp() < from_time.timestamp():
            return False
        return to_time is None or moment.timestamp() <= to_time.timestamp()

    limit = _integer(values.get("query.limit"), default=250, minimum=1, maximum=500)
    filtered = [item for item in items if visible(item)][:limit]
    result = {
        **dict(jsonable_encoder(payload)),
        "items": filtered,
        "tasks": filtered,
    }
    result["world_observation"] = _observation(
        operation="list",
        state="observed",
        origin=origin,
        count=len(filtered),
    )
    return result


def _normalized_reference(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _resolved_task(
    actor: ActorContext, values: Mapping[str, object], origin: str
) -> dict[str, object]:
    reference = str(values.get("query.ref") or "").strip()
    if not reference:
        raise HTTPException(status_code=422, detail="Task reference is required")
    scope = str(values.get("query.scope") or "mine")
    status_filter = str(values.get("query.status") or "").strip()
    payload = task_center.list_tasks(actor, scope=scope)
    items = [dict(jsonable_encoder(item)) for item in payload.get("items") or []]
    if status_filter:
        items = [item for item in items if item.get("status") == status_filter]

    normalized = _normalized_reference(reference)
    try:
        reference_uuid = str(UUID(reference))
    except ValueError:
        reference_uuid = ""

    scored: list[tuple[int, dict[str, object]]] = []
    for item in items:
        task_id = str(item.get("id") or "")
        title = _normalized_reference(item.get("title"))
        source_ref = _normalized_reference(item.get("source_entity_id"))
        score = 0
        if reference_uuid and task_id == reference_uuid:
            score = 1000
        elif normalized and title == normalized:
            score = 900
        elif normalized and source_ref == normalized:
            score = 850
        elif len(normalized) >= 4 and normalized in title:
            score = 500
        elif len(normalized) >= 8 and task_id.startswith(normalized):
            score = 450
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("title") or "")))
    candidates = [item for _score, item in scored[:12]]
    top_score = scored[0][0] if scored else 0
    top = [item for score, item in scored if score == top_score]
    exact = top_score >= 850
    selected = top[0] if exact and len(top) == 1 else None
    if selected is not None:
        selected = dict(jsonable_encoder(task_center.get_task(actor, str(selected["id"]))))
        state = "resolved"
    elif candidates:
        state = "ambiguous"
    else:
        state = "not_found"

    candidate_projection = [
        {
            key: item.get(key)
            for key in ("id", "title", "status", "version", "can_delete", "source_type")
        }
        for item in candidates
    ]
    observation = {
        "schema": "warehouse.world-observation.v1",
        "decision_owner": "auto_runtime",
        "workflow_prescribed": False,
        "semantic_resource": "workflow.task",
        "operation": "resolve",
        "state": state,
        "origin": origin,
        "reference": reference,
        "canonical_entity": (
            {"task_id": selected.get("id"), "version": selected.get("version")}
            if selected
            else None
        ),
        "observed": (
            {
                key: selected.get(key)
                for key in ("title", "status", "version", "can_delete", "source_type")
            }
            if selected
            else {}
        ),
        "candidates": candidate_projection,
        "uncertainties": (
            []
            if selected
            else [
                ("multiple_visible_task_candidates" if candidates else "no_visible_task_candidate")
            ]
        ),
        "affordances": [
            {"capability": "task_show", "effect": "observe_current_task_version"},
            {"capability": "task_list", "effect": "broaden_visible_task_search"},
        ],
    }
    return {
        "ok": selected is not None,
        "resolution": state,
        "reference": reference,
        "task": selected,
        "candidates": candidate_projection,
        "world_observation": observation,
    }


def execute_task_capability(
    tool_name: str,
    actor: ActorContext,
    values: Mapping[str, object],
    *,
    origin: str,
) -> dict[str, object]:
    """Execute one task gene and return current-state evidence."""
    if tool_name not in TASK_RUNTIME_TOOLS:
        raise RuntimeError(f"unsupported task runtime tool: {tool_name}")
    if tool_name == "task_meta":
        result = dict(jsonable_encoder(task_center.task_meta(actor)))
        result["world_observation"] = _observation(
            operation="metadata", state="observed", origin=origin
        )
        return result
    if tool_name == "task_list":
        return _filtered_task_list(actor, values, origin)
    if tool_name == "task_resolve":
        return _resolved_task(actor, values, origin)

    task_id = _path(values, "id") if tool_name != "task_create" else ""
    if tool_name == "task_show":
        task = dict(jsonable_encoder(task_center.get_task(actor, task_id)))
        task["world_observation"] = _observation(
            operation="read", state="observed", origin=origin, task=task
        )
        return task
    if tool_name == "task_history":
        result = dict(
            jsonable_encoder(
                task_center.task_history(
                    actor,
                    task_id,
                    limit=_integer(values.get("query.limit"), default=100, minimum=1, maximum=500),
                    before_id=(
                        int(values["query.before_id"])
                        if values.get("query.before_id") is not None
                        else None
                    ),
                )
            )
        )
        result["world_observation"] = _observation(
            operation="history",
            state="observed",
            origin=origin,
            count=len(result.get("items") or []),
        )
        return result

    payload = _body(values)
    if tool_name == "task_create":
        singular_assignee = payload.pop("assignee_user_id", None)
        if singular_assignee and not payload.get("assignees"):
            payload["assignees"] = [singular_assignee]
        created = task_center.create_task(actor, payload)
        observed = task_center.get_task(actor, str(created["id"]))
        return _task_result(
            observed,
            operation="create",
            intended=payload,
            origin=origin,
        )
    if tool_name == "task_update":
        observed, retries = _safe_versioned_write(actor, task_id, payload, "update")
        return _task_result(
            observed,
            operation="update",
            intended=payload,
            origin=origin,
            conflict_retries=retries,
        )
    if tool_name == "task_status":
        observed, retries = _safe_versioned_write(actor, task_id, payload, "status")
        return _task_result(
            observed,
            operation="status",
            intended={"status": payload.get("status")},
            origin=origin,
            conflict_retries=retries,
        )

    payload["confirm"] = True
    deleted = dict(jsonable_encoder(task_center.delete_task(actor, task_id, payload)))
    try:
        task_center.get_task(actor, task_id)
    except HTTPException as exc:
        gone = exc.status_code == status.HTTP_404_NOT_FOUND
    else:
        gone = False
    state = "verified" if gone else "verification_mismatch"
    deleted["verification"] = {
        "state": state,
        "semantic_resource": "workflow.task",
        "task_id": task_id,
        "deleted": gone,
    }
    deleted["world_observation"] = _observation(
        operation="delete",
        state=state,
        origin=origin,
        task={"id": task_id},
        verified_fields=["deleted"] if gone else [],
        mismatched_fields=[] if gone else ["deleted"],
    )
    return deleted
