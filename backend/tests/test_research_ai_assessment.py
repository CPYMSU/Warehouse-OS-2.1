from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services import research_ai_assessment as service, research_workflow as workflow


def actor(write=True):
    return SimpleNamespace(user_id=UUID(int=1), tenant_id=UUID(int=2),
                           permissions=frozenset({'research.read', 'research.write'} if write else {'research.read'}))


def rows():
    return {key: [] for key in ('files', 'dmp_history', 'protocols', 'runs', 'claims', 'evidence',
                                'reviews', 'executions', 'reproduction_checks', 'releases')}


SOURCE = {'file_version_id': str(UUID(int=5)), 'block_id': 'block-1', 'source_kind': 'document',
          'asset_class': 'manuscript', 'text': 'The model assumes a constant unit cost and a fixed charge.',
          'label': 'paper.docx', 'url': '/preview'}


def model_result(dimension='theory', *, defense='unassessed', evidence='insufficient', cited=False, argument=False):
    return {'summary': 'Provisional review of supplied material.', 'dimensions': [{
        'key': dimension, 'summary': 'Evidence and understanding are separate.', 'gaps': ['Check the assumptions.'],
        'citations': [], 'criteria': [{'key': key, 'evidence_verdict': evidence, 'defense_verdict': defense,
            'basis_source': 'defense_argument' if argument else 'project_evidence' if cited else 'insufficient',
            'basis': 'Only the supplied material was reviewed.', 'gaps': [],
            'citations': [{'file_version_id': SOURCE['file_version_id'], 'block_id': SOURCE['block_id'],
                           'quote': SOURCE['text']}] if cited else []}
            for key, _ in workflow.DASHBOARD_CHECKS[dimension][1]]}],
        'questions': [{'id': 'q1', 'dimension': dimension, 'criterion': workflow.DASHBOARD_CHECKS[dimension][1][0][0],
                       'question': 'Explain the assumption with one concrete example.'},
                      {'id': 'q2', 'dimension': dimension, 'criterion': workflow.DASHBOARD_CHECKS[dimension][1][1][0],
                       'question': 'What observation would contradict the explanation?'}]}


class Result:
    def __init__(self, values=None):
        self.values = values or []

    def mappings(self):
        return self

    def all(self):
        return self.values


@pytest.fixture
def state(monkeypatch):
    value = SimpleNamespace(version=0, content={'research_question': 'Keep manual notes',
        'research_dashboard_assessment': {'theory': {'items': {'assumptions': {'status': 'missing'}}}}},
        project={'id': UUID(int=3), 'title': 'Study', 'metadata': {}}, rows=rows(),
        calls=[], saved=[], locked=False, output=model_result(), mutate=None)
    value.rows['files'] = [{'file_id': str(UUID(int=4)), 'file_version_id': str(UUID(int=5)),
        'logical_path': 'manuscript/paper.docx', 'content_sha256': 'a' * 64, 'source_changed': False}]
    context = {'sources': [copy.deepcopy(SOURCE)], 'pinned_files': [{'file_version_id': str(UUID(int=5))}],
               'scope': {'truncated': False, 'characters': 100, 'included_blocks': 1}, 'manual_dmp_excerpt': 'Manual notes'}

    def snapshot(*args, **kwargs):
        return {'project': value.project, 'rows': copy.deepcopy(value.rows), 'content': copy.deepcopy(value.content),
                'version': value.version, 'dmp': {'version': value.version, 'content': copy.deepcopy(value.content)} if value.version else None,
                'fingerprint': service.assessment_fingerprint(value.project, value.rows, value.content)}

    @contextmanager
    def session(tenant):
        assert tenant == UUID(int=2)
        value.locked = True
        try:
            yield SimpleNamespace(execute=lambda *args: Result())
        finally:
            value.locked = False

    def completion(connection, **kwargs):
        assert not value.locked, 'Provider must never run while project lock is held'
        value.calls.append(kwargs)
        if value.mutate:
            value.mutate()
        return json.dumps(value.output)

    def save(session, actor, project, content):
        value.content.update(copy.deepcopy(content))
        value.version += 1
        value.saved.append(copy.deepcopy(value.content))
        return {'version': value.version, 'content': value.content}

    monkeypatch.setattr(service, '_snapshot', snapshot)
    monkeypatch.setattr(service, '_context', lambda *args: copy.deepcopy(context))
    monkeypatch.setattr(service, 'tenant_session', session)
    monkeypatch.setattr(service, '_project_row', lambda *args, **kwargs: value.project)
    monkeypatch.setattr(service, '_audit', lambda *args: None)
    monkeypatch.setattr(service, '_connection', lambda *args, **kwargs: SimpleNamespace(model='existing-balanced'))
    monkeypatch.setattr(service, 'chat_completion', completion)
    monkeypatch.setattr(workflow, '_save_dmp_revision', save)
    value.start = lambda **kwargs: service.run_ai_review(actor(), UUID(int=3),
        {'expected_dmp_version': value.version, 'dimension': 'theory', **kwargs}, Settings())
    value.reply = lambda review, **kwargs: service.run_ai_review(actor(), UUID(int=3), {
        'expected_dmp_version': value.version, 'expected_revision': review['revision'],
        'answer': 'My explanation is clearer, but I have not supplied new data.', 'question_id': 'q1', **kwargs},
        Settings(), review['id'])
    return value


def test_initial_review_is_fast_grounded_and_preserves_manual_assessment(state):
    manual = copy.deepcopy(state.content['research_dashboard_assessment'])
    result = state.start()
    review = result['review']
    assert len(state.calls) == 1 and state.calls[0]['thinking'] is False
    assert state.calls[0]['json_mode'] is True and state.calls[0]['max_tokens'] <= 2600
    assert SOURCE['text'] in state.calls[0]['user_prompt']
    assert state.content['research_dashboard_assessment'] == manual
    assert review['revision'] == 1 and review['provisional'] and len(review['result']['questions']) == 2
    readback = service.list_ai_reviews(actor(), UUID(int=3))
    assert readback['reviews'][0]['stale'] is False
    assert readback['reviews'][0]['history'][0]['kind'] == 'initial'


def test_answer_can_improve_defense_without_creating_scientific_evidence(state):
    review = state.start()['review']
    state.output = model_result(defense='clear')
    updated = state.reply(review)['review']
    dimension = updated['result']['dimensions'][0]
    assert dimension['evidence_verdict'] == 'insufficient' and dimension['defense_verdict'] == 'clear'
    assert dimension['defense_assessed_count'] == 1
    assert len(updated['history']) == 2 and updated['history'][0]['result'] == review['result']
    assert state.content['research_dashboard_assessment']['theory']['items']['assumptions']['status'] == 'missing'


def test_theory_argument_can_be_provisional_partial_and_later_reassessed_downward(state):
    review = state.start()['review']
    state.output = model_result(defense='clear', evidence='partial', argument=True)
    updated = state.reply(review)['review']
    criteria = updated['result']['dimensions'][0]['criteria']
    assert criteria[0]['evidence_verdict'] == 'partial' and criteria[0]['basis_source'] == 'defense_argument'
    assert not criteria[0]['citations'] and all(item['evidence_verdict'] != 'supported' for item in criteria)
    assert criteria[1]['evidence_verdict'] == 'insufficient'
    assert updated['result']['dimensions'][0]['evidence_verdict'] == 'partial'
    state.output = model_result(defense='developing', evidence='insufficient')
    lower = state.reply(updated)['review']
    assert lower['result']['dimensions'][0]['evidence_verdict'] == 'insufficient'
    assert lower['result']['dimensions'][0]['defense_verdict'] == 'developing'
    assert len(lower['history']) == 3


def test_new_material_requires_explicit_refresh_and_preserves_answer(state):
    review = state.start()['review']
    state.rows['files'][0]['content_sha256'] = 'b' * 64
    assert service.list_ai_reviews(actor(), UUID(int=3))['reviews'][0]['stale'] is True
    with pytest.raises(HTTPException) as error:
        state.reply(review)
    assert error.value.status_code == 409 and len(state.calls) == 1
    updated = state.reply(review, refresh_context=True)['review']
    assert updated['history'][-1]['context_refreshed'] is True
    assert updated['history'][-1]['answer'] == 'My explanation is clearer, but I have not supplied new data.'
    assert not service.list_ai_reviews(actor(), UUID(int=3))['reviews'][0]['stale']


@pytest.mark.parametrize('change', ['word', 'manual'])
def test_inflight_changes_reject_ai_save_and_preserve_latest_source(state, change):
    def mutate():
        if change == 'word':
            state.rows['files'][0]['content_sha256'] = 'c' * 64
        else:
            state.content['research_question'] = 'A newer manual research question'
            state.version += 1
    state.mutate = mutate
    with pytest.raises(HTTPException) as error:
        state.start()
    assert error.value.status_code == 409 and not state.saved
    assert service.SESSION_KEY not in state.content


@pytest.mark.parametrize('invalid', ['citation', 'criterion', 'question'])
def test_invalid_structured_provider_result_returns502_without_persisting(state, invalid):
    if invalid == 'citation':
        state.output = model_result(evidence='supported', cited=True)
        state.output['dimensions'][0]['criteria'][0]['citations'][0]['quote'] = 'Invented original source quotation'
    elif invalid == 'criterion':
        state.output['dimensions'][0]['criteria'][0]['key'] = 'made_up_quality'
    else:
        state.output['questions'][0]['id'] = 'q99'
    with pytest.raises(HTTPException) as error:
        state.start()
    assert error.value.status_code == 502 and not state.saved and service.SESSION_KEY not in state.content


def test_read_only_actor_and_stale_question_revision_never_call_provider(state):
    with pytest.raises(HTTPException) as error:
        service.run_ai_review(actor(False), UUID(int=3), {'expected_dmp_version': 0}, Settings())
    assert error.value.status_code == 403 and not state.calls
    review = state.start()['review']
    for patch, status in [({'expected_revision': 2}, 409), ({'question_id': 'not-this-review'}, 422)]:
        with pytest.raises(HTTPException) as error:
            state.reply(review, **patch)
        assert error.value.status_code == status
    assert len(state.calls) == 1


def test_paper_narrative_cannot_satisfy_data_verdict_or_answer_only_supported_claim():
    context = {'sources': [SOURCE]}
    result = service._validate_result(model_result('data', evidence='supported', cited=True), ['data'], context, answer='eloquent answer')
    assert result['dimensions'][0]['evidence_verdict'] == 'insufficient'
    assert all(item['gaps'] for item in result['dimensions'][0]['criteria'])
    with pytest.raises(ValueError, match='real project citations'):
        service._validate_result(model_result(evidence='supported', argument=True), ['theory'], context, answer='A proof without supplied source')


def test_partial_model_verdict_requires_a_real_project_citation():
    context = {'sources': [SOURCE]}
    output = model_result('model', evidence='partial')
    for basis_source in ('insufficient', 'project_evidence'):
        for item in output['dimensions'][0]['criteria']:
            item['basis_source'] = basis_source
        result = service._validate_result(output, ['model'], context, answer='An eloquent but unsupported answer')
        assert result['dimensions'][0]['evidence_verdict'] == 'insufficient'
    cited = service._validate_result(model_result('model', evidence='partial', cited=True), ['model'], context, answer='')
    assert cited['dimensions'][0]['evidence_verdict'] == 'partial'


def test_fingerprint_excludes_ai_history_and_indexing_but_tracks_saved_content():
    project = {'id': UUID(int=3), 'metadata': {}, 'updated_at': 'before'}
    actual = rows()
    actual['files'] = [{'file_id': 'f', 'file_version_id': 'v1', 'content_sha256': 'a', 'draft_id': 'd',
                        'draft_revision': 1, 'draft_content_hash': 'old', 'source_changed': False, 'index_status': 'queued'}]
    content = {'research_question': 'Original'}
    before = service.assessment_fingerprint(project, actual, content)
    content[service.SESSION_KEY] = {'review': {'history': ['self update']}}
    project['updated_at'] = 'later'
    actual['files'][0]['index_status'] = 'ready'
    assert service.assessment_fingerprint(project, actual, content) == before
    actual['files'][0]['draft_content_hash'] = 'new saved content'
    assert service.assessment_fingerprint(project, actual, content) != before
    actual['files'][0]['draft_content_hash'] = 'old'
    content['research_question'] = 'New manual question'
    assert service.assessment_fingerprint(project, actual, content) != before


@pytest.mark.parametrize('fresh', [True, False])
def test_context_prefers_current_saved_draft_but_never_mixes_stale_word(monkeypatch, fresh):
    project = {'id': UUID(int=3)}
    actual = rows()
    actual['files'] = [{'file_id': str(UUID(int=4)), 'file_version_id': str(UUID(int=5)),
                        'logical_path': 'paper.docx', 'file_kind': 'document'}]
    queries = []

    class Session:
        def execute(self, query, params):
            assert params['project_id'] == project['id']
            queries.append(str(query))
            if 'FROM research.file_versions' in str(query):
                return Result([{'file_version_id': UUID(int=5), 'file_id': UUID(int=4), 'version': 2,
                    'content_sha256': 'a' * 64, 'original_filename': 'paper.docx', 'extracted_text': 'Latest Word text',
                    'logical_path': 'paper.docx', 'file_kind': 'document', 'draft_id': UUID(int=7),
                    'base_file_version_id': UUID(int=5 if fresh else 6), 'draft_revision': 3,
                    'draft_blocks': [{'id': 'saved', 'type': 'paragraph', 'text': 'Current saved theoretical assumption',
                                      'source': {'latex': 'y=2x'}}]}])
            return Result([{'file_version_id': UUID(int=5), 'block_id': 'latest-word', 'block_type': 'paragraph',
                            'text': 'Latest Word theoretical assumption', 'heading_path': ['Theory']}])

    @contextmanager
    def session(tenant):
        yield Session()

    monkeypatch.setattr(service, 'tenant_session', session)
    context = service._context(actor(), {'project': project, 'rows': actual, 'content': {}}, ['theory'], [])
    assert context['pinned_files'][0]['url'].endswith('/content?version=2')
    texts = ' '.join(item['text'] for item in context['sources'])
    if fresh:
        assert 'Current saved' in texts and 'y=2x' in texts
        assert context['scope']['used_saved_drafts'] and len(queries) == 1
    else:
        assert 'Latest Word' in texts and 'Current saved' not in texts
        assert context['scope']['latest_word_instead_of_stale_draft'] == [str(UUID(int=4))]
