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
        output = copy.deepcopy(value.output)
        if json.loads(kwargs['user_prompt']).get('answer') and 'committee_feedback' not in output:
            output['committee_feedback'] = {'decision': 'needs_work', 'standard': 'Explain the assumption and its limit.',
                'reply': 'The answer names the assumption; the boundary still needs an example.',
                'next_action': 'Give an example that would violate the assumption.'}
        return json.dumps(output)

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
        **({'acknowledged_revision': review['revision']} if review['result'].get('committee_feedback') else {}),
        'answer': 'My explanation is clearer, but I have not supplied new data.', 'question_id': 'q1', **kwargs},
        Settings(), review['id'])
    return value


def test_initial_review_is_fast_grounded_and_preserves_manual_assessment(state):
    manual = copy.deepcopy(state.content['research_dashboard_assessment'])
    result = state.start()
    review = result['review']
    assert len(state.calls) == 1 and state.calls[0]['thinking'] is False
    assert state.calls[0]['json_mode'] is True and state.calls[0]['max_tokens'] == 6400
    assert SOURCE['text'] in state.calls[0]['user_prompt']
    assert state.content['research_dashboard_assessment'] == manual
    assert review['revision'] == 1 and review['provisional'] and len(review['result']['questions']) == 2
    readback = service.list_ai_reviews(actor(), UUID(int=3))
    assert readback['reviews'][0]['stale'] is False
    assert readback['reviews'][0]['history'][0]['kind'] == 'initial'


def test_question_source_aliases_resolve_only_to_actual_supplied_excerpts():
    second = {**SOURCE, 'file_version_id': str(UUID(int=6)), 'block_id': 'block-2',
              'text': 'Another real paragraph describing a different mechanism.'}
    context = {'sources': [SOURCE, second]}
    citations = service._question_source_excerpts(['S1', 'S2', 'block-1'], context)
    assert [item['quote'] for item in citations] == [SOURCE['text'], second['text'], SOURCE['text']]
    assert service._question_source_excerpts('S2', context)[0]['file_version_id'] == second['file_version_id']
    assert service._question_source_excerpts({'source_id': 'S1', 'block_id': 'block-1'}, context)[0]['quote'] == SOURCE['text']
    # A conflicting full ID, a file alone, and a guessed alias cannot select
    # a convenient but unrelated paragraph.
    for bad in ('S3', SOURCE['file_version_id'], {'source_id': 'S1', 'block_id': 'block-2'}):
        with pytest.raises(ValueError, match='Question source was not present'):
            service._question_source_excerpts([bad], context)


def test_question_source_strings_reject_ambiguous_block_or_alias():
    duplicate = {**SOURCE, 'file_version_id': str(UUID(int=6))}
    with pytest.raises(ValueError, match='Question source was not present'):
        service._question_source_excerpts(['block-1'], {'sources': [SOURCE, duplicate]})
    collision = {**duplicate, 'block_id': 'S1'}
    with pytest.raises(ValueError, match='Question source was not present'):
        service._question_source_excerpts(['S1'], {'sources': [SOURCE, collision]})


def test_economic_questions_require_a_verified_paper_excerpt_and_keep_the_hint():
    value = model_result('theory')
    value['questions'][0].update({'category': 'theory', 'hint': 'Check the assumptions.',
        'citations': [{'file_version_id': SOURCE['file_version_id'], 'block_id': SOURCE['block_id'], 'quote': SOURCE['text']}]})
    result = service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    assert result['questions'][0]['citations'][0]['quote'] == SOURCE['text']
    assert result['questions'][0]['citations'][0]['anchor_kind'] == 'source_excerpt'
    assert result['questions'][0]['category'] == 'theory' and result['questions'][0]['hint']
    value['questions'][0]['question'] = 'In the paper, ΔlnX_i=v_i x. Why is it linear?'
    with pytest.raises(ValueError, match='without rewriting'):
        service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    value['questions'][0]['question'] = 'As a thought experiment, if x=0.4, what must be checked?'
    assert service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    value['questions'][0]['hint'] = '先固定各參數在 0 和 1 之間。'
    safe = service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    assert safe['questions'][0]['hint'] == '先釐清原文的變量與假設，再比較不同條件下的結論。'
    value['questions'][0]['hint'] = '衝擊必然提高所有變量。'
    safe = service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    assert '必然' not in safe['questions'][0]['hint']
    # Model-written quotes are never presented as facts; excerpts come from the real block.
    value['questions'][0]['citations'][0]['quote'] = 'fabricated claim'
    result = service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    assert result['questions'][0]['citations'][0]['quote'] == SOURCE['text']
    value['questions'][0]['citations'][0]['block_id'] = 'unrelated-block'
    with pytest.raises(ValueError, match='Question source was not present'):
        service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    value['questions'][0]['citations'] = []
    with pytest.raises(ValueError, match='requires a verified manuscript citation'):
        service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    value['questions'][0].pop('category')
    with pytest.raises(ValueError, match='grounded economic theory'):
        service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='', require_economic_theory=True)
    # Older assessments and projects without readable theory stay usable.
    assert service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='')['questions']


def test_question_formula_comes_only_from_the_original_equation_block():
    original_latex = r'\pi_i \eta_i > \frac{\ln(1-v_i x)}{\ln(1-x)}'
    source = {**SOURCE, 'block_type': 'equation', 'text': 'threshold\n' + original_latex,
              'source_latex': original_latex}
    value = model_result('theory')
    value['questions'][0].update({'category': 'theory', 'source_refs': [{
        'file_version_id': source['file_version_id'], 'block_id': source['block_id'],
        'quote': 'invented', 'source_latex': 'invented'}]})
    result = service._validate_result(value, ['theory'], {'sources': [source]}, answer='', require_economic_theory=True)
    citation = result['questions'][0]['citations'][0]
    assert citation['quote'] == source['text'] and citation['source_latex'] == original_latex
    # Metadata unsupported by the original block must never be rendered as a source formula.
    source['source_latex'] = 'not in source'
    result = service._validate_result(value, ['theory'], {'sources': [source]}, answer='', require_economic_theory=True)
    assert 'source_latex' not in result['questions'][0]['citations'][0]


def test_question_math_accepts_only_complete_source_relations_not_wrong_variables():
    source = {**SOURCE, 'text': r'The approximation is \pi_i\eta_i > v_i. The exact sales relation is \Delta\ln M_i=\ln(1-v_i x).'}
    value = model_result('theory')
    value['questions'][0].update({'category': 'theory', 'source_refs': [{
        'file_version_id': source['file_version_id'], 'block_id': source['block_id']}],
        'question': r'在近似條件 \(\pi_i\eta_i > v_i\) 下，大幅變動會如何影響結論？'})
    assert service._validate_result(value, ['theory'], {'sources': [source]}, answer='', require_economic_theory=True)
    value['questions'][0]['question'] = '若 ΔlnX_i=v_i x，這個結論是否成立？'
    with pytest.raises(ValueError, match='without rewriting'):
        service._validate_result(value, ['theory'], {'sources': [source]}, answer='', require_economic_theory=True)
    value['questions'][0]['question'] = '若 πη>v，這個結論是否成立？'
    with pytest.raises(ValueError, match='without rewriting'):
        service._validate_result(value, ['theory'], {'sources': [source]}, answer='', require_economic_theory=True)
    value['questions'][0]['question'] = '若 π_iη_i≥v_i，這個結論是否成立？'
    with pytest.raises(ValueError, match='without rewriting'):
        service._validate_result(value, ['theory'], {'sources': [source]}, answer='', require_economic_theory=True)
    assert service._normalized_source_math(r'\pi_{ij}') != service._normalized_source_math(r'\pi_i j')
    assert service._normalized_source_math(r'\frac{a}{bc}') != service._normalized_source_math(r'\frac{ab}{c}')
    assert service._normalized_source_math(r'\pi_{i}') == service._normalized_source_math('πᵢ')
    # A prefix/suffix of a larger expression is not the same equation.
    relation = service._normalized_source_math(r'\pi_i\eta_i > v_i')
    assert not service._complete_math_relation_in_source(relation, service._normalized_source_math(
        r'The relation is \pi_i\eta_i > v_i + z_i.', preserve_spacing=True))
    assert not service._complete_math_relation_in_source(relation, service._normalized_source_math(
        r'The relation is \theta_i\pi_i\eta_i > v_i.', preserve_spacing=True))


def test_exact_formula_from_another_read_source_is_attached_to_question():
    formula = {**SOURCE, 'block_id': 'exact-formula', 'block_type': 'equation',
        'text': r'\pi_i\eta_i > v_i', 'source_latex': r'\pi_i\eta_i > v_i'}
    value = model_result('theory')
    value['questions'][0].update({'category': 'theory', 'source_refs': [{
        'file_version_id': SOURCE['file_version_id'], 'block_id': SOURCE['block_id']}],
        'question': r'在近似條件 \(\pi_i\eta_i > v_i\) 下，如何檢查結論？'})
    result = service._validate_result(value, ['theory'], {'sources': [SOURCE, formula]}, answer='', require_economic_theory=True)
    attached = result['questions'][0]['citations']
    assert [cite['block_id'] for cite in attached] == ['block-1', 'exact-formula']
    assert attached[1]['quote'] == formula['text'] and attached[1]['source_latex'] == formula['source_latex']


def test_invalid_equation_retries_once_with_natural_language_only(state, monkeypatch):
    state.project['metadata']['research_discipline'] = 'econometrics'
    source = {**SOURCE, 'text': SOURCE['text'] + ' The trade theory explains price mechanisms and their assumptions.'}
    context = {'sources': [source], 'pinned_files': [], 'scope': {}, 'manual_dmp_excerpt': ''}
    monkeypatch.setattr(service, '_context', lambda *args: copy.deepcopy(context))
    invalid = model_result('theory')
    invalid['questions'][0].update({'category': 'theory', 'question': '假設 ΔlnX_i=v_i x，這個推導成立嗎？',
        'source_refs': [{'file_version_id': source['file_version_id'], 'block_id': source['block_id']}]})
    valid = copy.deepcopy(invalid)
    valid['questions'][0]['question'] = '在來源中的假設改變時，推導仍然成立嗎？'
    calls = []
    def completion(_connection, **kwargs):
        calls.append(kwargs)
        return json.dumps(invalid if len(calls) == 1 else valid)
    monkeypatch.setattr(service, 'chat_completion', completion)
    result = state.start()
    assert len(calls) == 2 and '完全使用中文自然語言' in calls[1]['system_prompt']
    assert result['review']['result']['questions'][0]['question'] == valid['questions'][0]['question']


def test_economic_excerpts_include_mechanism_condition_equation_and_welfare_boundary():
    common = {'file_version_id': str(UUID(int=5)), 'asset_class': 'manuscript', 'source_kind': 'document'}
    candidates = [{**common, 'ordinal': 0, 'block_type': 'heading', 'text': 'Abstract'},
        {**common, 'ordinal': 1, 'block_type': 'paragraph', 'text': 'The income channel and valuation channel describe two different effects on economic activity.'},
        {**common, 'ordinal': 2, 'block_type': 'paragraph', 'text': 'The reversal threshold compares the competing movements under the stated assumptions.'},
        {**common, 'ordinal': 3, 'block_type': 'equation', 'text': 'x > ln(1-v*x) / ln(1-x)'},
        {**common, 'ordinal': 4, 'block_type': 'paragraph', 'text': 'This equation only applies within the specified parameter ranges and conditions.'},
        {**common, 'ordinal': 5, 'block_type': 'paragraph', 'text': 'The model studies bilateral sales, not welfare; the aggregate welfare implication remains open.'}]
    picked = service._economic_theory_excerpts(candidates)
    assert {item['ordinal'] for item in picked} >= {1, 2, 3, 4, 5}


def test_data_and_reference_scopes_keep_their_own_material_priority():
    assert service._theory_scope(['theory'])
    assert service._theory_scope(['paper'], {'key': 'hypothesis_model'})
    assert not service._theory_scope(['data'])
    assert not service._theory_scope(['paper'], {'key': 'reproduction'})
    assert not service._theory_scope(['paper'], focus_item={'key': 'references'})
    assert not service._theory_scope(['theory'], focus_item={'key': 'citations'})


def stage_result(dimension, stage_key, *, defense='unassessed', evidence='insufficient', cited=False):
    result = model_result(dimension, defense=defense, evidence=evidence, cited=cited)
    criterion = result['dimensions'][0]['criteria'][0]
    criterion['key'] = stage_key
    result['dimensions'][0]['criteria'] = [criterion]
    for question in result['questions']:
        question['criterion'] = stage_key
    return result


def test_checklist_item_has_own_committee_defense_and_does_not_change_manual_or_dimension_review(state):
    dimension = state.start()['review']
    manual = copy.deepcopy(state.content['research_dashboard_assessment'])
    state.output = stage_result('theory', 'assumptions', evidence='partial', cited=True)
    item = state.start(criterion_key='assumptions')['review']
    assert item['id'] != dimension['id'] and item['dimension'] == 'theory'
    assert item['criterion_key'] == 'assumptions' and item['criterion_label'] == '理論假設'
    assert [criterion['key'] for criterion in item['result']['dimensions'][0]['criteria']] == ['assumptions']
    prompt = json.loads(state.calls[-1]['user_prompt'])
    assert prompt['rubric'] == {'theory': {'assumptions': '理論假設'}}
    assert prompt['checklist_item']['record']['status'] == 'missing'
    assert all(q['criterion'] == 'assumptions' for q in item['result']['questions'])
    state.output = stage_result('theory', 'assumptions', defense='developing', evidence='partial', cited=True)
    defended = state.reply(item)['review']
    assert defended['result']['committee_feedback']['reply'] and len(defended['history']) == 2
    assert defended['history'][0]['result'] == item['result']
    assert state.content[service.SESSION_KEY][dimension['id']]['revision'] == 1
    assert state.content['research_dashboard_assessment'] == manual
    assert not next(r for r in service.list_ai_reviews(actor(), UUID(int=3))['reviews'] if r['id'] == item['id'])['stale']


def test_checklist_item_scope_is_validated_and_immutable(state):
    for payload in ({'dimension':'paper', 'criterion_key':'assumptions'},
                    {'dimension':'all', 'criterion_key':'question'},
                    {'stage_key':'question', 'criterion_key':'question'}):
        with pytest.raises(HTTPException) as error:
            state.start(**payload)
        assert error.value.status_code == 422
    assert not state.calls
    state.output = stage_result('paper', 'question')
    item = state.start(dimension='paper', criterion_key='question')['review']
    with pytest.raises(HTTPException) as error:
        state.reply(item, criterion_key='draft')
    assert error.value.status_code == 422 and len(state.calls) == 1


def test_every_dashboard_check_is_available_as_an_independent_defense_scope():
    for dimension, (_, checks) in workflow.DASHBOARD_CHECKS.items():
        for key, label in checks:
            item = service._criterion_for_review(dimension, key)
            assert item['key'] == key and item['label'] == label and item['fingerprint']


def test_item_rubric_change_marks_stale_and_requires_new_review(state, monkeypatch):
    state.output = stage_result('theory', 'assumptions')
    item = state.start(criterion_key='assumptions')['review']
    changed = list(workflow.DASHBOARD_CHECKS['theory'][1])
    changed[0] = ('assumptions', '更新後的理論假設')
    monkeypatch.setitem(workflow.DASHBOARD_CHECKS, 'theory', ('理論檢查', tuple(changed)))
    assert service.list_ai_reviews(actor(), UUID(int=3))['reviews'][0]['stale']
    with pytest.raises(HTTPException) as error:
        state.reply(item, refresh_context=True)
    assert error.value.status_code == 409 and len(state.calls) == 1


def test_single_item_dimension_normalization_still_verifies_citations():
    value = stage_result('paper', 'question', evidence='supported', cited=True)
    value['dimensions'][0]['key'] = 'question'
    for question in value['questions']:
        question['dimension'] = 'question'
    rubric = {'paper': {'question': '研究問題'}}
    result = service._validate_result(value, ['paper'], {'sources':[SOURCE]}, answer='', rubric=rubric, criterion_key='question')
    assert result['dimensions'][0]['key'] == 'paper' and result['questions'][0]['dimension'] == 'paper'
    value['dimensions'][0]['criteria'][0]['citations'][0]['quote'] = 'fabricated'
    sanitized = service._validate_result(value, ['paper'], {'sources':[SOURCE]}, answer='', rubric=rubric, criterion_key='question')
    item = sanitized['dimensions'][0]['criteria'][0]
    assert item['evidence_verdict'] == 'insufficient' and not item['citations'] and 'fabricated' not in json.dumps(item)


def test_specialist_stage_and_defense_keep_manual_progress_and_history(state):
    state.project['metadata']['research_discipline'] = 'econometrics'
    manual = copy.deepcopy(state.content['research_dashboard_assessment'])
    state.output = stage_result('theory', 'phenomenon', evidence='supported', cited=True)
    first = state.start(stage_key='phenomenon')['review']
    assert first['discipline'] == 'econometrics' and first['stage_key'] == 'phenomenon'
    assert first['stage_title'] in first['specialist']['name'] and first['dimension'] == 'theory'
    dimension = first['result']['dimensions'][0]
    assert dimension['criteria'][0]['key'] == 'phenomenon'
    assert dimension['evidence_verdict'] == 'partial'  # A manuscript statement is not observed data.
    assert '資料或分析產物' in dimension['criteria'][0]['gaps'][0]
    prompt = json.loads(state.calls[0]['user_prompt'])
    assert prompt['stage']['key'] == 'phenomenon' and prompt['rubric']['theory'] == {'phenomenon': first['stage_title']}
    assert prompt['specialists'][0]['name'] == first['specialist']['name']
    state.output = stage_result('theory', 'phenomenon', defense='clear', evidence='supported', cited=True)
    second = state.reply(first)['review']
    assert second['revision'] == 2 and len(second['history']) == 2
    assert second['result']['dimensions'][0]['defense_verdict'] == 'clear'
    assert state.content['research_dashboard_assessment'] == manual
    assert 'discipline_workflows' not in state.content


def test_single_stage_dimension_name_is_normalized_only_with_unique_stage_identity():
    response = stage_result('model', 'regularities', evidence='supported', cited=True)
    response['dimensions'][0]['key'] = 'regularities'
    for question in response['questions']:
        question['dimension'] = 'regularities'
    kwargs = {'answer': '', 'rubric': {'model': {'regularities': '估計模型與發現規律'}},
              'stage': {'key': 'regularities'}}
    result = service._validate_result(response, ['model'], {'sources': [SOURCE]}, **kwargs)
    assert result['dimensions'][0]['key'] == 'model'
    assert all(q['dimension'] == 'model' and q['criterion'] == 'regularities' for q in result['questions'])
    assert result['dimensions'][0]['evidence_verdict'] == 'partial'
    response['dimensions'][0]['criteria'][0]['key'] = 'other'
    with pytest.raises(ValueError):
        service._validate_result(response, ['model'], {'sources': [SOURCE]}, **kwargs)
    response['dimensions'][0]['criteria'][0]['key'] = 'regularities'
    response['dimensions'][0]['criteria'][0]['citations'][0]['quote'] = 'invented quote'
    sanitized = service._validate_result(response, ['model'], {'sources': [SOURCE]}, **kwargs)
    item = sanitized['dimensions'][0]['criteria'][0]
    assert item['evidence_verdict'] == 'insufficient' and not item['citations'] and 'invented quote' not in json.dumps(item)


def test_stage_rejects_unknown_or_changed_discipline_before_calling_provider(state):
    state.project['metadata']['research_discipline'] = 'econometrics'
    with pytest.raises(HTTPException) as error:
        state.start(stage_key='not_a_stage')
    assert error.value.status_code == 422 and not state.calls
    state.output = stage_result('theory', 'phenomenon')
    first = state.start(stage_key='phenomenon')['review']
    state.project['metadata']['research_discipline'] = 'theoretical_science'
    with pytest.raises(HTTPException) as error:
        state.reply(first, refresh_context=True)
    assert error.value.status_code == 409 and len(state.calls) == 1


def test_changed_stage_rubric_marks_review_stale_and_requires_new_review(state, monkeypatch):
    state.project['metadata']['research_discipline'] = 'econometrics'
    state.output = stage_result('theory', 'phenomenon')
    first = state.start(stage_key='phenomenon')['review']
    template = service.discipline_template('econometrics')
    next(item for item in template['stages'] if item['key'] == 'phenomenon')['prompt'] = 'Changed criterion'
    monkeypatch.setattr(service, 'discipline_template', lambda key: template)
    assert service.list_ai_reviews(actor(), UUID(int=3))['reviews'][0]['stale']
    with pytest.raises(HTTPException) as error:
        state.reply(first, refresh_context=True)
    assert error.value.status_code == 409 and len(state.calls) == 1


@pytest.mark.parametrize('discipline', ['data_science', 'engineering_science', 'theoretical_science', 'econometrics'])
def test_every_stage_has_a_discipline_specific_specialist_and_safe_scope(state, discipline):
    state.project['metadata']['research_discipline'] = discipline
    snapshot = {'project': state.project, 'content': state.content}
    template = service.discipline_template(discipline)
    assert len({stage['key'] for stage in template['stages']}) == len(template['stages'])
    for expected in template['stages']:
        resolved, stage, dimension, specialist = service._stage_for_review(snapshot, expected['key'])
        assert resolved == discipline and stage == expected and dimension in workflow.DASHBOARD_CHECKS
        assert template['title'] in specialist['name'] and stage['title'] in specialist['name']
        assert specialist['focus'] == stage['prompt']


def test_four_dimensions_get_distinct_real_specialist_prompts(state):
    for dimension in workflow.DASHBOARD_CHECKS:
        state.output = model_result(dimension)
        result = state.start(dimension=dimension)['review']
        assert result['specialist'] == service.SPECIALISTS[dimension]
        assert json.loads(state.calls[-1]['user_prompt'])['specialists'] == [service.SPECIALISTS[dimension]]
    assert len({item['name'] for item in service.SPECIALISTS.values()}) == 4


def test_split_single_dimension_is_safely_reassembled_with_verified_citations():
    response = model_result('paper', evidence='supported', cited=True)
    whole = response['dimensions'][0]
    response['dimensions'] = [{**whole, 'key': criterion['key'], 'criteria': [criterion]}
                              for criterion in whole['criteria']]
    response['questions'][0]['dimension'] = response['questions'][0]['criterion']
    result = service._validate_result(response, ['paper'], {'sources': [SOURCE]}, answer='')
    assert len(result['dimensions']) == 1 and result['dimensions'][0]['key'] == 'paper'
    assert len(result['dimensions'][0]['criteria']) == len(workflow.DASHBOARD_CHECKS['paper'][1])
    assert result['questions'][0]['dimension'] == 'paper'
    assert all(item['citations'][0]['quote'] == SOURCE['text'] for item in result['dimensions'][0]['criteria'])


def test_split_dimension_rejects_duplicates_and_unverified_citations():
    response = model_result('paper', evidence='supported', cited=True)
    whole = response['dimensions'][0]
    response['dimensions'] = [{**whole, 'key': criterion['key'], 'criteria': [criterion]}
                              for criterion in whole['criteria']]
    response['dimensions'][-1] = copy.deepcopy(response['dimensions'][0])
    with pytest.raises(ValueError, match='Wrong review dimensions'):
        service._validate_result(response, ['paper'], {'sources': [SOURCE]}, answer='')
    response['dimensions'][-1] = {**whole, 'key': whole['criteria'][-1]['key'], 'criteria': [whole['criteria'][-1]]}
    response['dimensions'][-1]['citations'] = [{
        'file_version_id': SOURCE['file_version_id'], 'block_id': SOURCE['block_id'], 'quote': 'fabricated'}]
    sanitized = service._validate_result(response, ['paper'], {'sources': [SOURCE]}, answer='')
    assert 'fabricated' not in json.dumps(sanitized)


def test_answer_can_improve_defense_without_creating_scientific_evidence(state):
    review = state.start()['review']
    state.output = model_result(defense='clear')
    updated = state.reply(review)['review']
    dimension = updated['result']['dimensions'][0]
    assert dimension['evidence_verdict'] == 'insufficient' and dimension['defense_verdict'] == 'clear'
    assert dimension['defense_assessed_count'] == 1
    assert len(updated['history']) == 2 and updated['history'][0]['result'] == review['result']
    assert state.content['research_dashboard_assessment']['theory']['items']['assumptions']['status'] == 'missing'


def test_committee_must_reply_before_acknowledged_next_defense_and_history_is_immutable(state):
    first = state.start()['review']
    original = copy.deepcopy(first['result'])
    state.output = model_result(defense='developing')
    first_reply = state.reply(first)['review']
    feedback = first_reply['result']['committee_feedback']
    assert feedback['decision'] == 'needs_work' and feedback['standard'] and feedback['reply'] and feedback['next_action']
    assert first_reply['history'][0]['result'] == original
    assert first_reply['history'][1]['result']['committee_feedback'] == feedback
    for acknowledged in (None, first_reply['revision'] - 1, True):
        with pytest.raises(HTTPException) as error:
            state.reply(first_reply, acknowledged_revision=acknowledged)
        assert error.value.status_code == 409
    assert len(state.calls) == 2 and state.version == 2
    state.output = model_result(defense='clear')
    state.output['committee_feedback'] = {'decision': 'meets_standard', 'standard': 'Explain the assumption and limit.',
        'reply': 'The example explains the assumption and when it breaks.', 'next_action': 'Check the cited evidence.'}
    second_reply = state.reply(first_reply)['review']
    assert second_reply['revision'] == 3 and second_reply['result']['committee_feedback']['decision'] == 'meets_standard'
    assert second_reply['history'][1]['result']['committee_feedback'] == feedback
    assert second_reply['history'][2]['answer']
    assert state.content['research_dashboard_assessment']['theory']['items']['assumptions']['status'] == 'missing'


def test_legacy_defense_without_committee_feedback_remains_usable(state):
    initial = state.start()['review']
    state.output = model_result(defense='clear')
    old = state.reply(initial)['review']
    old['result'].pop('committee_feedback')
    old['history'][-1]['result'].pop('committee_feedback', None)
    state.content[service.SESSION_KEY][old['id']] = copy.deepcopy(old)
    updated = state.reply(old)['review']
    assert updated['revision'] == 3 and updated['result']['committee_feedback']


def test_invalid_committee_response_retries_once_without_persisting_answer(state):
    initial = state.start()['review']
    state.output = model_result(defense='clear')
    state.output['committee_feedback'] = None
    with pytest.raises(HTTPException) as error:
        state.reply(initial)
    assert error.value.status_code == 502 and len(state.calls) == 3
    assert state.version == 1 and state.content[service.SESSION_KEY][initial['id']]['revision'] == 1


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


@pytest.mark.parametrize('invalid', ['criterion', 'question'])
def test_invalid_structured_provider_result_returns502_without_persisting(state, invalid):
    if invalid == 'criterion':
        state.output['dimensions'][0]['criteria'][0]['key'] = 'made_up_quality'
    else:
        state.output['questions'][0]['id'] = 'q99'
    with pytest.raises(HTTPException) as error:
        state.start()
    assert error.value.status_code == 502 and len(state.calls) == 2 and not state.saved and service.SESSION_KEY not in state.content


def test_invalid_format_retries_once_but_provider_failure_does_not(state, monkeypatch):
    calls = []
    valid = model_result()
    def completion(_connection, **kwargs):
        calls.append(kwargs)
        return '{"dimensions": [' if len(calls) == 1 else json.dumps(valid)
    monkeypatch.setattr(service, 'chat_completion', completion)
    assert state.start()['review']['revision'] == 1
    assert len(calls) == 2 and calls[0]['user_prompt'] == calls[1]['user_prompt']
    assert '逐字' in calls[1]['system_prompt']

    calls.clear()
    def unavailable(_connection, **kwargs):
        calls.append(kwargs)
        raise ConnectionError('provider unavailable')
    monkeypatch.setattr(service, 'chat_completion', unavailable)
    with pytest.raises(HTTPException) as error:
        state.start()
    assert error.value.status_code == 502 and len(calls) == 1


def test_invalid_citation_is_discarded_and_unsupported_judgment_downgraded(state, monkeypatch):
    valid = model_result(evidence='supported', cited=True)
    invalid = copy.deepcopy(valid)
    invalid['dimensions'][0]['criteria'][0]['citations'][0]['quote'] = 'Invented quotation'
    calls = []
    def completion(_connection, **kwargs):
        calls.append(kwargs)
        return json.dumps(invalid if len(calls) == 1 else valid)
    monkeypatch.setattr(service, 'chat_completion', completion)
    review = state.start()['review']
    assert len(calls) == 1 and len(state.saved) == 1
    first, second = review['result']['dimensions'][0]['criteria'][:2]
    assert first['evidence_verdict'] == 'insufficient' and not first['citations']
    assert '核對' in first['basis'] and second['citations'][0]['quote'] == SOURCE['text']
    assert 'Invented quotation' not in json.dumps(review)


def test_mixed_citations_keep_only_the_verified_source():
    value = model_result(evidence='supported', cited=True)
    item = value['dimensions'][0]['criteria'][0]
    item['citations'].append({**item['citations'][0], 'quote': 'invented quote'})
    result = service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='')
    checked = result['dimensions'][0]['criteria'][0]
    assert checked['evidence_verdict'] == 'supported' and len(checked['citations']) == 1
    assert checked['citations'][0]['quote'] == SOURCE['text'] and 'invented quote' not in json.dumps(result)
    assert any('略去' in gap for gap in checked['gaps'])


def test_only_unverified_citations_cannot_leave_an_unsupported_summary():
    value = model_result(evidence='supported', cited=True)
    value['summary'] = 'Unsupported claim'
    value['dimensions'][0]['summary'] = 'Unsupported claim'
    for item in value['dimensions'][0]['criteria']:
        item['citations'][0]['quote'] = 'invented'
    result = service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='')
    assert '未能逐字核對' in result['summary'] and '未能逐字核對' in result['dimensions'][0]['summary']
    assert all(item['evidence_verdict'] == 'insufficient' for item in result['dimensions'][0]['criteria'])


def test_defense_argument_remains_provisional_when_a_citation_is_discarded():
    value = model_result(evidence='supported', argument=True)
    item = value['dimensions'][0]['criteria'][0]
    item['citations'] = [{'file_version_id': SOURCE['file_version_id'], 'block_id': SOURCE['block_id'], 'quote': 'invented'}]
    result = service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='An actual theoretical argument')
    checked = result['dimensions'][0]['criteria'][0]
    assert checked['evidence_verdict'] == 'partial' and checked['basis_source'] == 'defense_argument'
    assert not checked['citations'] and 'invented' not in json.dumps(result)
    assert '暫定論證' in checked['basis'] and '未能核對' in checked['basis']
    assert any('未能逐字核對' in gap for gap in checked['gaps'])


def test_one_real_question_is_accepted_but_none_is_not_invented():
    value = model_result()
    value['questions'] = value['questions'][:1]
    assert len(service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='')['questions']) == 1
    value['questions'] = []
    with pytest.raises(ValueError, match='at least one'):
        service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='')
    value['questions'] = model_result()['questions']
    value['questions'].extend([{**value['questions'][0], 'id': 'q3'}, {**value['questions'][0], 'id': 'q4'}])
    assert len(service._validate_result(value, ['theory'], {'sources': [SOURCE]}, answer='')['questions']) == 3


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
    argument = service._validate_result(model_result(evidence='supported', argument=True), ['theory'], context, answer='A proof without supplied source')
    assert all(item['evidence_verdict'] == 'partial' for item in argument['dimensions'][0]['criteria'])


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


@pytest.mark.parametrize('scope', ['stage', 'item'])
def test_focused_context_prefers_pinned_data_and_excludes_old_manuscript(monkeypatch, scope):
    project = {'id': UUID(int=3), 'metadata': {'research_discipline': 'econometrics'}}
    current = rows()
    current['files'] = [
        {'file_id': str(UUID(int=4)), 'file_version_id': str(UUID(int=5)), 'logical_path': 'manuscript/paper.docx', 'file_kind': 'document'},
        {'file_id': str(UUID(int=7)), 'file_version_id': str(UUID(int=8)), 'logical_path': 'data/sample.csv', 'file_kind': 'dataset'},
    ]
    content = {'discipline_workflows': {'econometrics': {'phenomenon': {'artifacts': [
        {'file_version_id': str(UUID(int=9)), 'role': 'dataset'},
        {'file_version_id': str(UUID(int=6)), 'role': 'report'},
    ]}}}}
    if scope == 'item':
        content = {'research_dashboard_assessment': {'theory': {'items': {'assumptions': {
            'file_version_ids': [str(UUID(int=9)), str(UUID(int=6))]}}}}}
    versions = {
        UUID(int=5): (UUID(int=4), 2, 'manuscript/paper.docx', 'document'),
        UUID(int=6): (UUID(int=4), 1, 'manuscript/paper.docx', 'document'),
        UUID(int=8): (UUID(int=7), 2, 'data/sample.csv', 'dataset'),
        UUID(int=9): (UUID(int=7), 1, 'data/sample.csv', 'dataset'),
    }
    class Session:
        def execute(self, query, params):
            if 'FROM research.file_versions' in str(query):
                return Result([{'file_version_id': identifier, 'file_id': versions[identifier][0],
                    'version': versions[identifier][1], 'logical_path': versions[identifier][2], 'file_kind': versions[identifier][3],
                    'content_sha256': 'a' * 64, 'original_filename': 'sample', 'extracted_text': 'Extracted source.',
                    'draft_id': None, 'base_file_version_id': None, 'draft_revision': None, 'draft_blocks': []}
                    for raw in params['ids'] if (identifier := UUID(raw)) in versions])
            return Result([{'file_version_id': UUID(raw), 'block_id': 'source-' + raw, 'block_type': 'paragraph',
                            'text': 'Source text for version ' + raw, 'heading_path': []} for raw in params['ids']])
    @contextmanager
    def session(_tenant):
        yield Session()
    monkeypatch.setattr(service, 'tenant_session', session)
    stage = next(item for item in service.discipline_template('econometrics')['stages'] if item['key'] == 'phenomenon')
    context = service._context(actor(), {'project': project, 'rows': current, 'content': content}, ['theory'], [],
                               stage if scope == 'stage' else None,
                               {'key': 'assumptions'} if scope == 'item' else None)
    included = [item['file_version_id'] for item in context['sources']]
    assert included[0] == str(UUID(int=9))  # The stage's fixed data takes precedence over other excerpts.
    assert str(UUID(int=5)) in included and str(UUID(int=6)) not in included
    assert context['scope'][scope + '_artifacts_used'] == [str(UUID(int=9))]
    assert context['scope'][scope + '_artifacts_not_read'] == [str(UUID(int=6))]
