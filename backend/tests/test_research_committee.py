from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.services import research_committee as service


@pytest.fixture
def practice(monkeypatch):
    actor = SimpleNamespace(user_id=UUID(int=1), tenant_id=UUID(int=2), permissions=frozenset({'research.read', 'research.write'}))
    project = {'id': UUID(int=3), 'title': 'Research', 'metadata': {}}
    snapshot = {'project': project, 'version': 9, 'fingerprint': 'unchanged', 'content': {'manual': 'keep'}}
    records = {}
    locked = [False]

    class Result:
        def __init__(self, value=None): self.value = value
        def mappings(self): return self
        def all(self): return self.value or []
        def scalar_one_or_none(self): return self.value

    class Session:
        def execute(self, statement, params=None):
            sql = str(statement)
            params = params or {}
            if sql.startswith('INSERT INTO compatibility.documents'):
                assert params['key'] not in records
                import json
                records[params['key']] = {'payload': json.loads(params['payload']), 'version': 1}
                return Result()
            if sql.startswith('UPDATE compatibility.documents'):
                record = records.get(params['key'])
                if record is None or record['version'] != params['version']:
                    return Result()
                import json
                record['payload'] = json.loads(params['payload'])
                record['version'] += 1
                return Result(UUID(int=10))
            if sql.startswith('SELECT document_key,payload,version'):
                return Result([{'document_key': key, **value} for key, value in reversed(list(records.items())) if key.startswith(params['prefix'][:-1])])
            if sql.startswith('SELECT payload FROM compatibility.documents'):
                value = records.get(params['key'])
                return Result(deepcopy(value['payload']) if value else None)
            return Result()

    @contextmanager
    def tenant_session(tenant, user=None):
        assert tenant == actor.tenant_id
        locked[0] = True
        try:
            yield Session()
        finally:
            locked[0] = False

    def completion(connection, **kwargs):
        assert not locked[0], 'Provider calls must not hold a database transaction'
        return {'question': '你的研究對象是什麼？', 'hint': '先說對象。', 'source_id': 'S1',
                'feedback': {'reply': '你說明了研究對象。', 'next_action': '再補充範圍。'}}

    monkeypatch.setattr(service, 'tenant_session', tenant_session)
    monkeypatch.setattr(service.assessment, '_snapshot', lambda *a, **k: deepcopy(snapshot))
    monkeypatch.setattr(service.assessment, '_context', lambda *a, **k: {'sources': [
        {'asset_class': 'manuscript', 'source_id': 'S1', 'block_id': 'block-1', 'label': 'paper', 'text': 'A real excerpt.'}]})
    monkeypatch.setattr(service, '_project_row', lambda *a, **k: project)
    monkeypatch.setattr(service, '_audit', lambda *a, **k: None)
    monkeypatch.setattr(service, '_connection', lambda *a, **k: SimpleNamespace(model='test-model'))
    monkeypatch.setattr(service, 'chat_completion', completion)
    return SimpleNamespace(actor=actor, snapshot=snapshot, records=records, project=project)


def test_21_member_practice_preserves_manual_work_and_history(practice):
    start = service.start_committee(practice.actor, practice.project['id'], None)
    session = start['session']
    assert len(start['professors']) == 21
    assert session['current']['professor_id'] == 1
    for index in range(21):
        assert session['current']['professor_id'] == index + 1
        response = service.answer_committee(practice.actor, practice.project['id'], UUID(session['id']),
                                            {'expected_revision': session['revision'], 'answer': '我的研究對象是雙邊貿易。'}, None)
        session = response['session']
    assert session['status'] == 'completed' and session['current'] is None
    assert len(session['turns']) == 21 and session['turns'][-1]['feedback']['reply']
    assert practice.snapshot['version'] == 9 and practice.snapshot['content'] == {'manual': 'keep'}
    listed = service.list_committee(practice.actor, practice.project['id'])
    assert listed['session']['id'] == session['id'] and len(listed['sessions'][0]['turns']) == 21


def test_stale_revision_and_changed_material_keep_answer_history(practice):
    session = service.start_committee(practice.actor, practice.project['id'], None)['session']
    identifier = UUID(session['id'])
    with pytest.raises(HTTPException) as stale:
        service.answer_committee(practice.actor, practice.project['id'], identifier,
                                 {'expected_revision': 2, 'answer': 'answer'}, None)
    assert stale.value.status_code == 409
    practice.snapshot['fingerprint'] = 'changed'
    with pytest.raises(HTTPException) as changed:
        service.answer_committee(practice.actor, practice.project['id'], identifier,
                                 {'expected_revision': 1, 'answer': 'answer'}, None)
    assert changed.value.status_code == 409
    assert next(iter(practice.records.values()))['payload']['turns'] == []


def test_read_permission_and_verified_source_are_required(practice):
    practice.actor.permissions = frozenset({'research.write'})
    with pytest.raises(HTTPException) as denied:
        service.start_committee(practice.actor, practice.project['id'], None)
    assert denied.value.status_code == 403
    with pytest.raises(ValueError):
        service._parse_model({'question': 'Question?', 'hint': '', 'source_id': 'invented'},
                             [{'id': 'real'}], needs_question=True, needs_feedback=False)


def test_concurrent_answer_is_not_overwritten(practice, monkeypatch):
    session = service.start_committee(practice.actor, practice.project['id'], None)['session']
    record = next(iter(practice.records.values()))

    def other_request_finishes(connection, **kwargs):
        record['version'] = 2
        record['payload']['revision'] = 2
        record['payload']['turns'] = [{'answer': 'another answer'}]
        return {'question': '下一題？', 'hint': '', 'source_id': 'S1',
                'feedback': {'reply': '回答清楚。', 'next_action': '繼續。'}}

    monkeypatch.setattr(service, 'chat_completion', other_request_finishes)
    with pytest.raises(HTTPException) as conflict:
        service.answer_committee(practice.actor, practice.project['id'], UUID(session['id']),
                                 {'expected_revision': 1, 'answer': 'my answer'}, None)
    assert conflict.value.status_code == 409
    assert record['payload']['turns'] == [{'answer': 'another answer'}]
