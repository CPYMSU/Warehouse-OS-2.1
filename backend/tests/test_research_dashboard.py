from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.services import research_workflow as workflow


def actor(write=True):
    return SimpleNamespace(tenant_id=UUID(int=2), user_id=UUID(int=1),
        permissions=frozenset({'research.read', 'research.write'} if write else {'research.read'}))


def rows():
    return {key: [] for key in ('files', 'dmp_history', 'protocols', 'runs', 'claims', 'evidence',
                                'reviews', 'reproduction_checks', 'executions', 'releases')}


PROJECT = {'id': UUID(int=3), 'metadata': {'research_discipline': 'econometrics'}}


def dimension(dashboard, key):
    return next(item for item in dashboard['dimensions'] if item['key'] == key)


def test_registered_paper_and_results_do_not_invent_completed_checks_or_current_stage():
    actual = rows()
    actual['files'] = [{'file_id': str(UUID(int=4)), 'file_version_id': str(UUID(int=5)),
                       'logical_path': 'manuscript/MK73_main_EN.docx', 'display_name': 'English paper.docx',
                       'file_kind': 'document', 'version': 1, 'version_count': 1, 'draft_revision': 0,
                       'source_changed': False, 'index_status': 'ready'}]
    actual['claims'] = [{'status': 'accepted'}]
    actual['executions'] = [{'status': 'succeeded'}]
    dashboard = workflow._research_dashboard(PROJECT, actual, None, {})
    assert all(item['completed'] is None and item['status'] == 'unassessed' for item in dashboard['dimensions'])
    assert dimension(dashboard, 'paper')['facts']['manuscripts'] == 1
    assert dimension(dashboard, 'paper')['facts']['saved_drafts'] == 1
    assert dimension(dashboard, 'data')['facts']['data_files'] == 0
    assert dimension(dashboard, 'theory')['facts']['accepted_claims'] == 1
    assert dimension(dashboard, 'model')['facts']['successful_executions'] == 1
    assert dashboard['stage_graph']['current_stage'] is None
    assert all(item['status'] == 'unassessed' for item in dashboard['stage_graph']['nodes'])
    assert 'percent' not in json.dumps(dashboard)


def test_explicit_zero_is_distinct_from_unknown_and_manual_blocker_has_next_action():
    content = {'research_dashboard_assessment': {'data': {'items': {'sources': {'status': 'missing'}}}},
               'discipline_workflows': {'econometrics': {'question': {'status': 'blocked', 'notes': 'Need a research question',
                                                                     'blockers': 'Specify the comparison'}}}}
    dashboard = workflow._research_dashboard(PROJECT, rows(), {'version': 2, 'content': content}, {})
    assert dimension(dashboard, 'data')['completed'] == 0
    assert dimension(dashboard, 'data')['assessed_count'] == 1
    assert dimension(dashboard, 'theory')['completed'] is None
    assert dashboard['stage_graph']['current_stage'] == 'question'
    assert dashboard['next_action']['action']['dimension'] == 'data'
    assert any(item['action'].get('stage_key') == 'question' for item in dashboard['blockers'])


def test_readback_drops_foreign_evidence_instead_of_exposing_its_link():
    identifier = str(UUID(int=99))
    content = {'research_dashboard_assessment': {'theory': {'items': {
        'assumptions': {'status': 'in_progress', 'file_version_ids': [identifier]}}}}}
    dashboard = workflow._research_dashboard(PROJECT, rows(), {'version': 1, 'content': content}, {})
    item = dimension(dashboard, 'theory')['items'][0]
    assert item['file_version_ids'] == [] and item['evidence'] == []
    assert identifier not in json.dumps(dashboard)


class Result:
    def __init__(self, value=None):
        self.value = value

    def mappings(self):
        return self

    def one_or_none(self):
        return self.value

    def one(self):
        return self.value

    def all(self):
        return self.value or []


@pytest.fixture
def state(monkeypatch):
    value = SimpleNamespace(revisions=[], audits=[], queries=[], owned={str(UUID(int=6))})

    class Session:
        def execute(self, query, params):
            sql = ' '.join(str(query).split())
            value.queries.append((sql, params))
            assert params.get('project_id', PROJECT['id']) == PROJECT['id']
            if sql.startswith('SELECT') and 'FROM research.dmp_revisions' in sql:
                return Result(copy.deepcopy(value.revisions[-1]) if value.revisions else None)
            if sql.startswith('UPDATE research.dmp_revisions'):
                value.revisions[-1]['status'] = 'superseded'
                return Result()
            if sql.startswith('INSERT INTO research.dmp_revisions'):
                saved = {**params, 'content': json.loads(params['content']), 'status': 'draft'}
                value.revisions.append(copy.deepcopy(saved))
                return Result(copy.deepcopy(saved))
            if 'FROM research.file_versions v JOIN research.files f' in sql:
                return Result([{'file_version_id': identifier, 'file_id': str(UUID(int=4)),
                                'version': 1, 'logical_path': 'manuscript/paper.docx'}
                               for identifier in params['version_ids'] if identifier in value.owned])
            raise AssertionError(sql)

    @contextmanager
    def session(tenant):
        assert tenant == UUID(int=2)
        yield Session()

    def project(session, reference, *, lock=False):
        if str(reference) != str(PROJECT['id']):
            raise HTTPException(status_code=404, detail='Project not found')
        value.project_locked = lock
        return copy.deepcopy(PROJECT)

    monkeypatch.setattr(workflow, 'tenant_session', session)
    monkeypatch.setattr(workflow, '_project_row', project)
    monkeypatch.setattr(workflow, '_audit', lambda *args: value.audits.append(args[-1]))
    return value


def save(version, item, project=PROJECT['id'], write=True):
    return workflow.save_research_assessment(actor(write), project, {
        'expected_dmp_version': version, 'assessment': {'theory': {'items': {'assumptions': item}}}})


def test_manual_assessment_is_versioned_and_merges_other_dmp_and_stage_notes(state):
    first = workflow.save_dmp(actor(), PROJECT['id'], {'content': {'research_question': 'Keep the question',
        'discipline_workflows': {'econometrics': {'question': {'status': 'in_progress', 'notes': 'Keep stage notes'}}}}})
    original = copy.deepcopy(first['dmp']['content'])
    result = save(1, {'status': 'ready', 'note': 'Explicit assumptions recorded', 'file_version_ids': [str(UUID(int=6))]})
    assert state.project_locked is True and result['dmp']['version'] == 2
    assert first['dmp']['content'] == original
    assert result['dmp']['content']['research_question'] == original['research_question']
    assert result['dmp']['content']['discipline_workflows'] == original['discipline_workflows']
    assert result['assessment']['theory']['updated_by'] == str(UUID(int=1))
    later = workflow.save_dmp(actor(), PROJECT['id'], {'content': {'hypothesis': 'Keep the manual assessment'}})
    assert later['dmp']['content']['research_dashboard_assessment'] == result['assessment']


def test_global_version_conflict_and_cross_project_reference_do_not_create_revision(state):
    save(0, {'status': 'in_progress'})
    for call, status in [(lambda: save(0, {'status': 'ready'}), 409),
                         (lambda: save(1, {'status': 'ready', 'file_version_ids': [str(UUID(int=99))]}), 422),
                         (lambda: save(1, {'status': 'ready'}, project=UUID(int=99)), 404)]:
        with pytest.raises(HTTPException) as error:
            call()
        assert error.value.status_code == status
    assert len(state.revisions) == 1


@pytest.mark.parametrize('item', [{'status': 'proved'}, {'confidence': 100},
                                 {'file_version_ids': ['https://example.org/internal']}])
def test_invalid_assessments_are_not_saved(state, item):
    with pytest.raises(HTTPException) as error:
        save(0, item)
    assert error.value.status_code == 422 and not state.revisions


def test_read_only_actor_cannot_save_and_get_summary_does_not_write(state, monkeypatch):
    with pytest.raises(HTTPException) as error:
        save(0, {'status': 'ready'}, write=False)
    assert error.value.status_code == 403
    monkeypatch.setattr(workflow, '_workflow_rows', lambda *args: rows())
    result = workflow.workflow_detail(actor(False), PROJECT['id'])
    assert result['research_dashboard']['dmp_version'] == 0
    assert not state.revisions and not state.audits and not state.queries


def test_workflow_queries_batch_all_file_versions_without_per_file_roundtrips():
    queries = []

    class Session:
        def execute(self, query, params):
            queries.append((str(query), params))
            return Result([])

    result = workflow._workflow_rows(Session(), PROJECT['id'])
    assert result['files'] == [] and len(queries) <= 12
    assert all(params == {'project_id': PROJECT['id']} for _, params in queries)
    assert all(not query.lstrip().startswith(('INSERT', 'UPDATE', 'DELETE')) for query, _ in queries)
