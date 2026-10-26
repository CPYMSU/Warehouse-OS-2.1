from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.deps import ActorContext
from app.services import research_vault as vault
from app.services import research_workflow as workflow
from app.services.research_disciplines import (
    discipline_catalogue, discipline_key, discipline_workflow, project_discipline,
)


def actor(*permissions):
    return ActorContext(user_id=UUID(int=1), tenant_id=UUID(int=2), tenant_slug="test",
                        tenant_name="Test", industry_template_key="research_lab", username="test",
                        display_name="Test", role_level=10, topology_level=10, topology_title="Test",
                        permissions=frozenset(permissions))


class Result:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def one(self):
        assert self.row is not None
        return self.row

    def one_or_none(self):
        return self.row


class ResearchState:
    def __init__(self):
        self.project = {"id": UUID(int=3), "metadata": {"retained": "keep"}, "research_area": "Institutional economics"}
        self.revisions = []
        self.audit = []

    def execute(self, statement, params):
        sql = " ".join(str(statement).split())
        if sql.startswith("SELECT") and "FROM research.dmp_revisions" in sql:
            return Result(copy.deepcopy(self.revisions[-1]) if self.revisions else None)
        if sql.startswith("UPDATE research.dmp_revisions"):
            self.revisions[-1]["status"] = "superseded"
            return Result()
        if sql.startswith("INSERT INTO research.dmp_revisions"):
            row = {**params, "content": json.loads(params["content"]), "status": "draft"}
            self.revisions.append(copy.deepcopy(row))
            return Result(copy.deepcopy(row))
        if sql.startswith("UPDATE research.projects SET metadata"):
            self.project["metadata"] = json.loads(params["metadata"])
            return Result()
        raise AssertionError("Unexpected research query: " + sql)


@pytest.fixture
def state(monkeypatch):
    state = ResearchState()

    @contextmanager
    def session(tenant_id):
        assert tenant_id == UUID(int=2)
        yield state

    def project_row(session, project_ref, lock=False):
        assert lock, "Every mutation must hold the project lock"
        if str(project_ref) != str(state.project["id"]):
            raise HTTPException(404, "Research project not found")
        return copy.deepcopy(state.project)

    for module in (vault, workflow):
        monkeypatch.setattr(module, "tenant_session", session)
        monkeypatch.setattr(module, "_project_row", project_row)
        monkeypatch.setattr(module, "_audit", lambda session, actor, action, details: state.audit.append((action, details)))
    return state


def classify(state, key, **extra):
    return vault.set_project_discipline(actor("research.write"), state.project["id"], {"discipline": key, **extra})


def save_stage(state, key="question", **extra):
    return workflow.save_discipline_stage(actor("research.write"), state.project["id"], key, {
        "discipline": "econometrics", "notes": "What changes Y when X changes?",
        "status": "completed", "expected_revision": 0, **extra,
    })


def test_four_templates_and_requested_econometrics_sequence():
    catalogue = discipline_catalogue()
    assert [item["key"] for item in catalogue] == ["data_science", "engineering_science", "theoretical_science", "econometrics"]
    assert len({tuple(stage["key"] for stage in item["stages"]) for item in catalogue}) == 4
    assert [stage["key"] for stage in catalogue[-1]["stages"]] == [
        "question", "database", "econometric_model", "regularities", "phenomenon", "hypothesis_model",
        "substitution", "dynamic_equilibrium", "boundaries", "case_analysis", "reproduction",
    ]
    catalogue[-1]["stages"].clear()
    assert len(discipline_catalogue()[-1]["stages"]) == 11
    assert discipline_key("计量经济学") == "econometrics"
    assert project_discipline({"research_area": "DATA SCIENCE"}) == "data_science"
    assert project_discipline({"research_area": "CHEMISTRY / COMPUTATION"}) is None
    assert project_discipline({"metadata": {"research_discipline": None}, "research_area": "ECONOMETRICS"}) is None


def test_notes_are_versioned_and_survive_generic_dmp_saves_and_discipline_changes(state):
    classify(state, "econometrics")
    first = save_stage(state)
    first_content = copy.deepcopy(first["dmp"]["content"])
    workflow.save_dmp(actor("research.write"), state.project["id"], {"content": {"research_question": "Shared research question"}})
    classify(state, "data_science", expected_discipline="econometrics")
    save_stage(state, discipline="data_science", notes="Predictive evaluation plan")
    classify(state, "econometrics")
    result = save_stage(state, "database", notes="Dataset key is region and year", status="in_progress")
    latest = state.revisions[-1]["content"]
    assert latest["research_question"] == "Shared research question"
    assert latest["discipline_workflows"]["econometrics"]["question"]["notes"] == "What changes Y when X changes?"
    assert latest["discipline_workflows"]["data_science"]["question"]["notes"] == "Predictive evaluation plan"
    assert first["dmp"]["content"] == first_content
    assert [item["version"] for item in state.revisions] == [1, 2, 3, 4]
    assert [item["status"] for item in state.revisions] == ["superseded"] * 3 + ["draft"]
    assert result["discipline_workflow"]["completed"] == 1
    assert state.project["metadata"]["retained"] == "keep"


def test_conflicting_stage_and_classification_writes_do_not_overwrite(state):
    classify(state, "econometrics")
    save_stage(state)
    with pytest.raises(HTTPException) as conflict:
        save_stage(state, notes="Stale draft")
    assert conflict.value.status_code == 409
    assert len(state.revisions) == 1
    assert state.revisions[0]["content"]["discipline_workflows"]["econometrics"]["question"]["notes"] != "Stale draft"
    with pytest.raises(HTTPException) as conflict:
        classify(state, "data_science", expected_discipline="theoretical_science")
    assert conflict.value.status_code == 409
    assert project_discipline(state.project) == "econometrics"


@pytest.mark.parametrize("payload", [
    {"notes": "", "status": "completed"}, {"notes": []}, {"notes": "x" * 32001},
    {"status": []}, {"status": "verified"}, {"expected_revision": True}, {"expected_revision": -1},
    {"discipline": "unknown"}, {"discipline": []},
])
def test_invalid_stage_data_is_rejected_without_writing(state, payload):
    classify(state, "econometrics")
    with pytest.raises(HTTPException) as error:
        save_stage(state, **payload)
    assert error.value.status_code == 422
    assert not state.revisions


def test_wrong_project_or_discipline_cannot_receive_a_stage(state):
    classify(state, "data_science")
    with pytest.raises(HTTPException) as error:
        save_stage(state)
    assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        workflow.save_discipline_stage(actor("research.write"), uuid4(), "question", {
            "discipline": "econometrics", "expected_revision": 0,
        })
    assert error.value.status_code == 404
    assert not state.revisions


def test_read_only_and_high_level_accounts_without_write_permission_cannot_mutate(state):
    for identity in (actor(), actor("research.read")):
        with pytest.raises(HTTPException) as error:
            vault.set_project_discipline(identity, state.project["id"], {"discipline": "econometrics"})
        assert error.value.status_code == 403
        with pytest.raises(HTTPException) as error:
            workflow.save_discipline_stage(identity, state.project["id"], "question", {})
        assert error.value.status_code == 403
    assert state.project["metadata"] == {"retained": "keep"}
    assert not state.revisions


def test_unknown_classification_does_not_silently_become_another_discipline(state):
    with pytest.raises(HTTPException) as error:
        classify(state, "macroeconomics")
    assert error.value.status_code == 422
    assert project_discipline(state.project) is None
