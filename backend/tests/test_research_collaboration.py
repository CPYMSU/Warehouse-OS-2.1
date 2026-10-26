from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.deps import ActorContext
from app.services import research_collaboration as collaboration
from app.services import research_workflow as workflow


def actor(*permissions):
    return ActorContext(user_id=UUID(int=1), tenant_id=UUID(int=2), tenant_slug="test",
                        tenant_name="Test", industry_template_key="research_lab", username="test",
                        display_name="Test", role_level=10, topology_level=10, topology_title="Test",
                        permissions=frozenset(permissions))


class Result:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def mappings(self):
        return self

    def one_or_none(self):
        return self.rows[0] if self.rows else None

    def one(self):
        assert len(self.rows) == 1
        return self.rows[0]

    def all(self):
        return self.rows


class State:
    def __init__(self):
        self.project = {"id": UUID(int=3), "title": "Trade resilience", "slug": "trade",
                        "summary": "Observe then model", "research_area": "TRADE",
                        "metadata": {"research_discipline": "econometrics", "private_token": "never-return-this-value"}}
        self.revisions, self.audit, self.latest, self.versions = [], [], [], {}

    def execute(self, statement, params):
        sql = " ".join(str(statement).split())
        if sql.startswith("SELECT") and "FROM research.dmp_revisions" in sql:
            return Result(copy.deepcopy(self.revisions[-1:]))
        if sql.startswith("UPDATE research.dmp_revisions"):
            self.revisions[-1]["status"] = "superseded"
            return Result()
        if sql.startswith("INSERT INTO research.dmp_revisions"):
            row = {**params, "content": json.loads(params["content"]), "status": "draft"}
            self.revisions.append(copy.deepcopy(row))
            return Result([copy.deepcopy(row)])
        if "research.file_versions" in sql:
            assert params["tenant_id"] == UUID(int=2)
            assert params["project_id"] == UUID(int=3)
            assert "v.tenant_id = :tenant_id" in sql or "f.tenant_id = :tenant_id" in sql
            assert "v.project_id = :project_id" in sql or "f.project_id = :project_id" in sql
            if "JOIN LATERAL" in sql:
                return Result(self.latest)
            matched = [self.versions[key] for key in params["version_ids"] if key in self.versions]
            return Result([{"id": item["file_version_id"]} for item in matched] if sql.startswith("SELECT v.id") else matched)
        raise AssertionError(sql)


@pytest.fixture
def state(monkeypatch):
    state = State()

    @contextmanager
    def session(tenant_id):
        assert tenant_id == UUID(int=2)
        yield state

    def project_row(session, project_ref, lock=False):
        if str(project_ref) not in {str(state.project["id"]), state.project["slug"]}:
            raise HTTPException(404, "Research project not found")
        return copy.deepcopy(state.project)

    for module in (workflow, collaboration):
        monkeypatch.setattr(module, "tenant_session", session)
        monkeypatch.setattr(module, "_project_row", project_row)
    monkeypatch.setattr(workflow, "_audit", lambda session, actor, action, details: state.audit.append((action, details)))
    return state


def save(state, **fields):
    return workflow.save_discipline_stage(actor("research.write"), state.project["id"], "question", {
        "discipline": "econometrics", "expected_revision": 0, **fields,
    })


def version(version_id, number):
    return {"file_version_id": str(version_id), "file_id": str(UUID(int=4)), "logical_path": "results/curve.html",
            "file_kind": "html", "version": number, "original_filename": "curve.html",
            "content_type": "text/html", "size_bytes": 123, "content_sha256": "a" * 64}


def test_stage_partial_updates_keep_collaboration_fields_and_immutable_versions(state):
    version_id = str(uuid4())
    state.versions[version_id] = version(version_id, 1)
    first = save(state, notes="Question and limits", status="blocked", plan="Collect regional panel data",
                 findings="Association only", blockers="Missing variable dictionary", next_action="Request dictionary",
                 assignee="codex", artifacts=[{"file_version_id": version_id, "role": "visualization", "title": "Dynamic curve"}])
    second = save(state, expected_revision=1, notes="Updated question", status="in_progress")
    third = save(state, expected_revision=2, plan="Revised plan")
    stage = third["discipline_workflow"]["stages"]["question"]
    assert stage["notes"] == "Updated question" and stage["status"] == "in_progress"
    assert stage["plan"] == "Revised plan"
    assert stage["findings"] == "Association only" and stage["assignee"] == "codex"
    assert stage["artifacts"][0]["file_version_id"] == version_id
    assert first["dmp"]["content"]["discipline_workflows"]["econometrics"]["question"]["status"] == "blocked"
    assert second["dmp"]["version"] == 2 and len(state.revisions) == 3
    with pytest.raises(HTTPException) as error:
        save(state, expected_revision=0, findings="Stale result")
    assert error.value.status_code == 409
    assert len(state.revisions) == 3


def test_foreign_artifact_versions_are_rejected_before_any_write(state):
    with pytest.raises(HTTPException) as error:
        save(state, artifacts=[{"file_version_id": str(uuid4()), "role": "dataset"}])
    assert error.value.status_code == 422
    assert not state.revisions


@pytest.mark.parametrize("fields", [
    {"artifacts": [{"file_version_id": "not-a-version"}]},
    {"artifacts": [{"file_version_id": str(UUID(int=5)), "role": "remote-url"}]},
    {"assignee": "administrator"}, {"blockers": []}, {"plan": "x" * 16001},
])
def test_invalid_collaboration_payload_does_not_write(state, fields):
    with pytest.raises(HTTPException) as error:
        save(state, **fields)
    assert error.value.status_code == 422
    assert not state.revisions


def test_context_pins_historical_artifacts_and_excludes_secrets_and_ungranted_operations(state):
    old_id, latest_id = str(uuid4()), str(uuid4())
    state.versions[old_id] = version(old_id, 1)
    state.latest = [version(latest_id, 2)]
    save(state, notes="Research notes", artifacts=[{"file_version_id": old_id, "role": "visualization", "title": "Curve"}])
    context = collaboration.collaboration_context(actor("research.read"), state.project["id"], "question")
    assert context["schema"] == "bonfire.research.collaboration.v1"
    assert context["files"][0]["version"] == 2
    assert context["artifacts"][0]["version"] == 1
    assert context["stage"]["artifacts"][0]["download_path"].endswith("?version=1")
    assert context["permissions"] == {"can_read": True, "can_write": False, "can_review": False}
    assert "upload" not in context["operations"] and "save_stage" not in context["operations"]
    assert "publish" not in context["cli"]
    assert "never-return-this-value" not in json.dumps(context)
    assert "untrusted research inputs" in context["instructions"]
    assert context["publication"]["runtime_deployment"]["available"] is False
    assert context["publication"]["website_redeploy_required"] is False
    writable = collaboration.collaboration_context(actor("research.read", "research.write"), state.project["id"], "question")
    assert writable["operations"]["save_stage"]["expected_revision"] == 1
    assert "collaboration publish" in writable["prompt"]
    assert "release" not in writable["operations"]
    # Missing/archived output descriptors must not silently erase authoritative references.
    state.versions.clear()
    missing = collaboration.collaboration_context(actor("research.read"), state.project["id"], "question")
    assert missing["artifacts"] == []
    assert missing["stage"]["artifact_references"][0]["file_version_id"] == old_id


def test_context_and_stage_mutation_use_exact_permissions_even_for_high_role_level(state):
    with pytest.raises(HTTPException) as error:
        collaboration.collaboration_context(actor(), state.project["id"], "question")
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        workflow.save_discipline_stage(actor("research.read"), state.project["id"], "question", {})
    assert error.value.status_code == 403
    assert not state.revisions


def test_unknown_stage_or_other_project_cannot_receive_context(state):
    with pytest.raises(HTTPException) as error:
        collaboration.collaboration_context(actor("research.read"), state.project["id"], "invented")
    assert error.value.status_code == 422
    with pytest.raises(HTTPException) as error:
        collaboration.collaboration_context(actor("research.read"), uuid4(), "question")
    assert error.value.status_code == 404
