from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from fastapi import HTTPException

from app.api.deps import ActorContext
from app.main import app as _app  # noqa: F401 - configures native capability routes
from app.services import auto_runtime, task_runtime
from app.terminal import executor, legacy_catalog
from app.terminal.catalog import (
    ai_capability_candidates,
    business_action_catalogue,
    entry_by_tool_name,
)


class _AuditWriter:
    def record(self, **_kwargs: object) -> str:
        return "00000000-0000-0000-0000-000000000099"


def _actor() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000002"),
        tenant_slug="example",
        tenant_name="Example",
        industry_template_key="power_system",
        username="owner",
        display_name="Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset({"tasks.read", "tasks.create", "tasks.manage"}),
    )


def test_task_actions_fill_shared_business_command_topology() -> None:
    actions = {
        item["tool_name"]: item
        for item in business_action_catalogue(_actor())
        if item["tool_name"] in task_runtime.TASK_RUNTIME_TOOLS
    }

    assert set(actions) == task_runtime.TASK_RUNTIME_TOOLS
    assert all(item["available"] is True for item in actions.values())
    assert all(item["adapter"] == "verified_registry" for item in actions.values())
    assert all(item["semantic_resource"] == "workflow.task" for item in actions.values())
    assert all(item["execution_identity"] == "requesting_user" for item in actions.values())
    assert all("postgresql_rls" in item["verification"] for item in actions.values())
    assert actions["task_delete"]["confirmation_policy"] == {
        "mode": "passkey",
        "adapter": "staged_action",
    }
    assert actions["task_delete"]["manual_execution"] == "governed_confirmation"
    assert actions["task_delete"]["semantic_contract"]["confirmation_binding"] == {
        "semantic_resource": "workflow.task",
        "id_argument": "id",
        "id_field": "task_id",
        "version_argument": "version",
        "version_field": "version",
        "resolve_capabilities": ["task_resolve", "task_show", "task_list"],
        "require_current_observation": True,
    }

    update_schema = legacy_catalog.tool_schema(entry_by_tool_name("task_update"))["function"][
        "parameters"
    ]
    assert "kind" in update_schema["properties"]
    assert "start" in update_schema["properties"]
    assert "end" in update_schema["properties"]
    assert "owner-org" in update_schema["properties"]
    assert "minutes" not in update_schema["properties"]
    assert "progress" not in update_schema["properties"]
    assert "task_status" in {
        item["tool_name"] for item in ai_capability_candidates("完成毕业论文任务", limit=12)
    }
    assert ai_capability_candidates("修改任务日期", limit=3)[0]["tool_name"] == "task_update"
    assert ai_capability_candidates("删除任务", limit=3)[0]["tool_name"] == "task_delete"
    assert ai_capability_candidates("按名称定位任务", limit=3)[0]["tool_name"] == "task_resolve"


def test_task_resolve_exposes_canonical_identity_without_guessing(monkeypatch) -> None:
    task_id = "10000000-0000-0000-0000-000000000001"
    candidates = [
        {
            "id": task_id,
            "title": "蔡培元的畢業論文",
            "status": "cancelled",
            "version": 3,
            "can_delete": True,
            "source_type": "manual",
        },
        {
            "id": "10000000-0000-0000-0000-000000000002",
            "title": "蔡培元的畢業論文備份",
            "status": "planned",
            "version": 1,
            "can_delete": True,
            "source_type": "manual",
        },
    ]
    monkeypatch.setattr(
        task_runtime.task_center,
        "list_tasks",
        lambda _actor_value, scope: {"items": deepcopy(candidates), "scope": scope},
    )
    monkeypatch.setattr(
        task_runtime.task_center,
        "get_task",
        lambda _actor_value, supplied_id: deepcopy(
            next(item for item in candidates if item["id"] == supplied_id)
        ),
    )

    resolved = task_runtime.execute_task_capability(
        "task_resolve",
        _actor(),
        {"query.ref": "蔡培元的畢業論文", "query.scope": "mine"},
        origin="auto_runtime",
    )

    assert resolved["resolution"] == "resolved"
    assert resolved["task"]["id"] == task_id
    assert resolved["world_observation"]["canonical_entity"] == {
        "task_id": task_id,
        "version": 3,
    }
    assert resolved["world_observation"]["decision_owner"] == "auto_runtime"
    assert resolved["world_observation"]["workflow_prescribed"] is False

    ambiguous = task_runtime.execute_task_capability(
        "task_resolve",
        _actor(),
        {"query.ref": "蔡培元的畢業論文", "query.status": "planned"},
        origin="auto_runtime",
    )
    assert ambiguous["resolution"] == "ambiguous"
    assert ambiguous["task"] is None
    assert ambiguous["world_observation"]["canonical_entity"] is None


def test_auto_runtime_binds_delete_to_observed_identity_and_version() -> None:
    task_id = "10000000-0000-0000-0000-000000000001"
    entry = entry_by_tool_name("task_delete")
    evidence = [
        {
            "tool_name": "task_show",
            "result": {
                "data": {
                    "world_observation": {
                        "schema": "warehouse.world-observation.v1",
                        "decision_owner": "auto_runtime",
                        "workflow_prescribed": False,
                        "semantic_resource": "workflow.task",
                        "operation": "read",
                        "state": "observed",
                        "canonical_entity": {"task_id": task_id, "version": 3},
                    }
                }
            },
        }
    ]

    assert (
        auto_runtime._confirmation_binding_failure(entry, {"id": task_id, "version": 3}, evidence)
        is None
    )

    stale = auto_runtime._confirmation_binding_failure(
        entry, {"id": task_id, "version": 1}, evidence
    )
    assert stale["status"] == "resource_version_changed"
    assert stale["data"]["world_observation"]["observed_candidates"] == [
        {"id": task_id, "version": 3, "state": "observed", "operation": "read"}
    ]
    assert {
        item["tool_name"] for item in stale["data"]["atomic_recovery"]["available_capabilities"]
    } >= {
        "task_resolve",
        "task_show",
        "task_list",
    }

    wrong_identity = auto_runtime._confirmation_binding_failure(
        entry,
        {"id": "10000000-0000-0000-0000-000000000099", "version": 3},
        evidence,
    )
    assert wrong_identity["status"] == "resource_identity_unbound"
    assert wrong_identity["data"]["world_observation"]["canonical_entity"] is None


def test_task_runtime_rebases_safe_update_and_emits_readback_evidence(monkeypatch) -> None:
    task = {
        "id": "10000000-0000-0000-0000-000000000001",
        "title": "Original title",
        "description": None,
        "kind": "task",
        "category": "work",
        "status": "planned",
        "priority": "normal",
        "visibility": "private",
        "start_at": None,
        "end_at": None,
        "due_at": "2026-08-05T18:00:00+08:00",
        "all_day": False,
        "timezone": "Asia/Shanghai",
        "location": None,
        "owner_org_unit_id": None,
        "plan_id": None,
        "version": 4,
        "assignees": [{"id": str(_actor().user_id)}],
    }

    monkeypatch.setattr(
        task_runtime.task_center,
        "get_task",
        lambda _actor_value, _task_id: deepcopy(task),
    )

    def update(_actor_value, _task_id, payload):
        assert payload["expected_version"] == task["version"]
        task.update({key: value for key, value in payload.items() if key != "expected_version"})
        task["version"] += 1
        return deepcopy(task)

    monkeypatch.setattr(task_runtime.task_center, "update_task", update)

    result = task_runtime.execute_task_capability(
        "task_update",
        _actor(),
        {
            "path.id": task["id"],
            "body.expected_version": 2,
            "body.title": "Rebased title",
            "body.kind": "event",
            "body.start_at": "2026-08-06T09:00:00+08:00",
            "body.end_at": "2026-08-06T10:00:00+08:00",
            "body.due_at": "",
        },
        origin="auto_runtime",
    )

    assert result["title"] == "Rebased title"
    assert result["kind"] == "event"
    assert result["due_at"] == ""
    assert result["verification"]["state"] == "verified"
    assert result["verification"]["conflict_retries"] == 1
    assert result["world_observation"]["schema"] == "warehouse.world-observation.v1"
    assert result["world_observation"]["semantic_resource"] == "workflow.task"
    assert result["world_observation"]["decision_owner"] == "auto_runtime"

    def update_status(_actor_value, _task_id, payload):
        assert payload == {"status": "completed", "expected_version": task["version"]}
        task["status"] = "completed"
        task["version"] += 1
        return deepcopy(task)

    monkeypatch.setattr(task_runtime.task_center, "update_task_status", update_status)
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    envelope = executor.execute_runtime_tool_call(
        _actor(),
        "task_status",
        {
            "id": task["id"],
            "status": "completed",
            "version": task["version"],
        },
    )

    assert envelope["ok"] is True
    assert envelope["status"] == "succeeded"
    assert envelope["data"]["status"] == "completed"
    assert envelope["data"]["verification"]["state"] == "verified"


def test_task_runtime_list_filters_and_delete_stays_passkey_governed(monkeypatch) -> None:
    actor = _actor()
    items = [
        {
            "id": "10000000-0000-0000-0000-000000000001",
            "title": "Graduation thesis",
            "description": "Finish the final chapter",
            "status": "planned",
            "source_type": "manual",
            "due_at": "2026-08-05T18:00:00+08:00",
            "version": 3,
        },
        {
            "id": "10000000-0000-0000-0000-000000000002",
            "title": "Completed filing",
            "description": "Archive only",
            "status": "completed",
            "source_type": "record",
            "due_at": "2026-08-08T18:00:00+08:00",
            "version": 2,
        },
    ]
    monkeypatch.setattr(
        task_runtime.task_center,
        "list_tasks",
        lambda _actor_value, scope: {"items": items, "tasks": items, "scope": scope},
    )

    listed = task_runtime.execute_task_capability(
        "task_list",
        actor,
        {
            "query.scope": "mine",
            "query.status": "planned",
            "query.q": "thesis",
            "query.from": "2026-08-05T00:00:00+08:00",
            "query.to": "2026-08-06T00:00:00+08:00",
            "query.limit": 50,
        },
        origin="auto_runtime",
    )

    assert [item["title"] for item in listed["items"]] == ["Graduation thesis"]
    assert listed["world_observation"]["count"] == 1

    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    monkeypatch.setattr(
        task_runtime,
        "execute_task_capability",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must be staged")),
    )
    pending = executor.execute_runtime_tool_call(
        actor,
        "task_delete",
        {"id": items[0]["id"], "version": items[0]["version"]},
    )

    assert pending["status"] == "confirmation_required"
    assert pending["data"]["confirmation_policy"] == {
        "mode": "passkey",
        "adapter": "staged_action",
    }


def test_task_runtime_delete_verifies_absence_after_authorized_execution(monkeypatch) -> None:
    task_id = "10000000-0000-0000-0000-000000000001"
    deleted = False

    def delete(_actor_value, supplied_id, payload):
        nonlocal deleted
        assert supplied_id == task_id
        assert payload == {"expected_version": 7, "confirm": True}
        deleted = True
        return {
            "ok": True,
            "deleted": True,
            "task_id": supplied_id,
            "collaboration_removed": False,
            "detached_plan_tasks": 0,
        }

    def get(_actor_value, supplied_id):
        assert supplied_id == task_id
        if deleted:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"id": task_id, "version": 7}

    monkeypatch.setattr(task_runtime.task_center, "delete_task", delete)
    monkeypatch.setattr(task_runtime.task_center, "get_task", get)

    result = task_runtime.execute_task_capability(
        "task_delete",
        _actor(),
        {
            "path.id": task_id,
            "body.expected_version": 7,
            "body.confirm": True,
        },
        origin="auto_runtime",
    )

    assert result["deleted"] is True
    assert result["verification"] == {
        "state": "verified",
        "semantic_resource": "workflow.task",
        "task_id": task_id,
        "deleted": True,
    }
    assert result["world_observation"]["state"] == "verified"
