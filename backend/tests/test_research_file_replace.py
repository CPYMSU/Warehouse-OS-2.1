from __future__ import annotations

import copy
import io
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.api import research as api
from app.core.config import Settings
from app.services import research_refinement as refinement, research_vault as vault
from app.services.object_storage import LocalContentAddressedObjectStore


def test_rebase_schedules_missing_translation_without_waiting_for_ai(monkeypatch):
    calls = []
    original = {"ok": True, "draft": {"revision": 6}, "snapshot": {"sha256": "old"}}
    monkeypatch.setattr(api, "rebase_refinement", lambda *args: original.copy())
    def queue(user, project, file, payload):
        calls.append((user, project, file, payload))
        return {"accepted": True, "run_id": "run-1", "status": "queued"}
    monkeypatch.setattr(api, "queue_semantic_run", queue)
    tasks = BackgroundTasks()
    user = actor()
    settings = Settings()
    response = api.research_manuscript_rebase("project", "file", tasks, user, settings, {"expected_revision": 5})
    assert response["snapshot"] == original["snapshot"]
    assert response["translation_auto"]["status"] == "queued"
    assert calls == [(user, "project", "file", {"modes": ["translate"]})]
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func is api.run_semantic_ai
    assert tasks.tasks[0].args == (user, "run-1", settings)


def test_rebase_keeps_saved_version_when_translation_queue_fails(monkeypatch):
    monkeypatch.setattr(api, "rebase_refinement", lambda *args: {"ok": True, "snapshot": {"sha256": "old"}})
    def fail(*args):
        raise RuntimeError("private provider detail")
    monkeypatch.setattr(api, "queue_semantic_run", fail)
    tasks = BackgroundTasks()
    response = api.research_manuscript_rebase("project", "file", tasks, actor(), Settings(), {})
    assert response["ok"] and response["snapshot"]["sha256"] == "old"
    assert response["translation_auto"]["status"] == "failed"
    assert response["translation_auto"]["retryable"] is True
    assert "private provider detail" not in str(response)
    assert not tasks.tasks


def test_rebase_does_not_launch_duplicate_processing_run_or_queue_after_conflict(monkeypatch):
    tasks = BackgroundTasks()
    monkeypatch.setattr(api, "rebase_refinement", lambda *args: {"ok": True})
    monkeypatch.setattr(api, "queue_semantic_run", lambda *args: {"run_id": "existing", "status": "processing"})
    response = api.research_manuscript_rebase("project", "file", tasks, actor(), Settings(), {})
    assert response["translation_auto"]["status"] == "processing" and not tasks.tasks
    def conflict(*args):
        raise HTTPException(status_code=409, detail="Draft or source Word changed")
    monkeypatch.setattr(api, "rebase_refinement", conflict)
    def unexpected(*args):
        pytest.fail("Conflicted rebases must not enqueue translation")
    monkeypatch.setattr(api, "queue_semantic_run", unexpected)
    with pytest.raises(HTTPException) as error:
        api.research_manuscript_rebase("project", "file", tasks, actor(), Settings(), {})
    assert error.value.status_code == 409


def actor(write=True):
    return SimpleNamespace(user_id=UUID(int=1), tenant_id=UUID(int=2),
                           permissions=frozenset({'research.read', 'research.write'} if write else {'research.read'}))


class Result:
    def __init__(self, value=None):
        self.value = value

    def mappings(self):
        return self

    def one_or_none(self):
        return self.value

    def one(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


@pytest.fixture
def upload(monkeypatch, tmp_path):
    state = SimpleNamespace(file={'id': UUID(int=4), 'logical_path': 'manuscript/paper.docx'},
                            current=UUID(int=5), sql=[], writes=[])
    store = LocalContentAddressedObjectStore(tmp_path / 'objects')
    stored = store.put_stream(tenant_id=UUID(int=2), stream=io.BytesIO(b'new contents'), max_bytes=100)

    class Session:
        def execute(self, query, params):
            sql = ' '.join(str(query).split())
            state.sql.append(sql)
            if sql.startswith('SELECT * FROM research.files'):
                assert sql.endswith('FOR UPDATE')
                return Result(state.file)
            if sql.startswith('SELECT id FROM research.file_versions'):
                assert params['file_id'] == UUID(int=4)
                return Result(state.current)
            if sql.startswith('SELECT COALESCE(max(version)'):
                return Result(2)
            if sql.startswith('INSERT INTO research.file_versions'):
                state.writes.append(params)
                return Result()
            if sql.startswith('UPDATE research.file_versions'):
                version = state.writes[-1]
                return Result({**version, 'version': version['version'], 'original_filename': version['original_filename'],
                               'git_sha': 'commit', 'created_at': 'now', 'preview': {}})
            if sql.startswith('UPDATE research.files'):
                return Result()
            raise AssertionError(sql)

    @contextmanager
    def session(tenant):
        assert tenant == UUID(int=2)
        yield Session()

    def project(session, project_ref, *, lock):
        assert lock is True
        return {'id': UUID(int=3), 'default_branch': 'main'}

    monkeypatch.setattr(vault, 'tenant_session', session)
    monkeypatch.setattr(vault, '_project_row', project)
    monkeypatch.setattr(vault, 'analyse_object', lambda *args: SimpleNamespace(file_kind='document', extracted_text='', preview={}))
    monkeypatch.setattr(vault, '_record_commit', lambda *args: ('commit', None, {}))
    monkeypatch.setattr(vault, '_audit', lambda *args: None)
    state.call = lambda **kwargs: vault.add_file_version(actor(kwargs.pop('write', True)), UUID(int=3),
        stored=stored, store=store, original_filename='new-local.docx', content_type=None,
        logical_path='manuscript/paper.docx', commit_message='Update', settings=Settings(), **kwargs)
    return state


def test_matching_upload_guard_preserves_file_identity_and_appends_version(upload):
    result = upload.call(expected_file_version_id=str(UUID(int=5)))
    assert result['file']['id'] == str(UUID(int=4))
    assert result['version']['version'] == 2 and len(upload.writes) == 1
    assert upload.writes[0]['original_filename'] == 'new-local.docx'
    assert not any('DELETE' in sql or 'manuscript_drafts' in sql for sql in upload.sql)


@pytest.mark.parametrize('missing', [False, True])
def test_stale_or_missing_replace_target_rejects_before_mutation(upload, missing):
    if missing:
        upload.file = None
    with pytest.raises(HTTPException) as error:
        upload.call(expected_file_version_id=str(UUID(int=8)))
    assert error.value.status_code == 409 and not upload.writes
    assert not any(sql.startswith(('UPDATE', 'INSERT', 'DELETE')) for sql in upload.sql)


def test_upload_guard_is_optional_and_permission_is_still_required(upload):
    assert upload.call()['version']['version'] == 2
    upload.sql.clear()
    with pytest.raises(HTTPException) as error:
        upload.call(write=False, expected_file_version_id=str(UUID(int=5)))
    assert error.value.status_code == 403 and not upload.sql
    with pytest.raises(HTTPException) as error:
        upload.call(expected_file_version_id='invalid')
    assert error.value.status_code == 422 and not upload.sql


def test_api_forwards_guard_without_scheduling_a_model(monkeypatch, tmp_path):
    observed = {}
    monkeypatch.setattr(api, 'add_file_version', lambda *args, **kwargs: observed.update(kwargs) or {'ok': True, 'version': {}})
    api.research_file_upload('project', actor(), Settings(asset_storage_root=tmp_path),
        file=UploadFile(file=io.BytesIO(b'word'), filename='local.docx'), logical_path='paper.docx',
        commit_message='Replace', expected_sha256=None, background_tasks=None,
        expected_file_version_id=UUID(int=5))
    assert observed['expected_file_version_id'] == UUID(int=5)


@pytest.fixture
def rebase(monkeypatch, tmp_path):
    state = SimpleNamespace(
        project={'id': UUID(int=3), 'title': 'Study'},
        file={'id': UUID(int=4), 'logical_path': 'manuscript/paper.docx', 'display_name': 'local.docx'},
        latest={'id': UUID(int=6), 'version': 2, 'original_filename': 'local.docx',
                'storage_provider': 'content_addressed_hdd', 'content_sha256': 'b' * 64},
        current=UUID(int=6), commits=[], audits=[], events=[], fail_update=False,
        draft={'id': UUID(int=7), 'tenant_id': UUID(int=2), 'project_id': UUID(int=3), 'file_id': UUID(int=4),
               'base_file_version_id': UUID(int=5), 'revision': 9, 'state': 'active', 'updated_at': 'yesterday',
               'submitted_at': None, 'created_by': UUID(int=1), 'updated_by': UUID(int=1),
               'blocks': [{'id': 'old', 'type': 'paragraph', 'text': 'Saved edits with 𝑋 and \u03b1',
                           'source': {'preserved': True}}]},
        fresh=[{'id': 'new', 'type': 'paragraph', 'text': 'Updated Word source'}],
    )
    state.store = LocalContentAddressedObjectStore(tmp_path / 'objects')

    class Session:
        def execute(self, query, params):
            sql = ' '.join(str(query).split())
            if sql.startswith('SELECT id FROM research.files'):
                assert sql.endswith('FOR UPDATE')
                state.events.append('file_lock')
                return Result(state.file['id'])
            if sql.startswith('SELECT id FROM research.file_versions'):
                state.events.append('latest_read')
                return Result(state.current)
            if sql.startswith('SELECT * FROM research.manuscript_drafts'):
                assert sql.endswith('FOR UPDATE')
                state.events.append('draft_lock')
                return Result(copy.deepcopy(state.draft))
            if sql.startswith('UPDATE research.manuscript_drafts'):
                if state.fail_update:
                    raise RuntimeError('injected update failure')
                state.draft.update(base_file_version_id=params['version_id'], blocks=json.loads(params['blocks']),
                                   revision=state.draft['revision'] + 1, updated_at='now')
                return Result(copy.deepcopy(state.draft))
            if sql.startswith('SELECT git_sha, manifest FROM research.commits'):
                assert params['project_id'] == UUID(int=3) and params['file_id'] == str(UUID(int=4))
                assert "->>'file_id'=:file_id" in sql
                return Result(state.commits[-1] if state.commits else None)
            raise AssertionError(sql)

    @contextmanager
    def session(tenant):
        assert tenant == UUID(int=2)
        previous = copy.deepcopy((state.draft, state.commits, state.audits))
        try:
            yield Session()
        except Exception:
            state.draft, state.commits, state.audits = previous
            raise

    def project(*args, **kwargs):
        assert kwargs['lock'] is True
        state.events.append('project_lock')
        return state.project

    def record(session, actor, settings, project, message, *, manifest_extra):
        state.commits.append({'git_sha': 'snapshot-commit', 'manifest': copy.deepcopy(manifest_extra)})
        return 'snapshot-commit', None, manifest_extra

    monkeypatch.setattr(refinement, 'tenant_session', session)
    monkeypatch.setattr(refinement, '_target_rows', lambda *args: (state.project, state.file, state.latest))
    monkeypatch.setattr(refinement, '_project_row', project)
    monkeypatch.setattr(refinement, '_initial_blocks', lambda *args: copy.deepcopy(state.fresh))
    monkeypatch.setattr(refinement, 'object_store_for_provider', lambda *args: state.store)
    monkeypatch.setattr(refinement, '_source_path', lambda settings, archive: state.store.path_for(archive['object_key']))
    monkeypatch.setattr(refinement, '_record_commit', record)
    monkeypatch.setattr(refinement, '_audit', lambda *args: state.audits.append(args[-1]))
    state.call = lambda **kwargs: refinement.rebase_refinement(actor(kwargs.pop('write', True)), UUID(int=3), UUID(int=4),
        {'expected_revision': 9, 'expected_file_version_id': str(UUID(int=6)), **kwargs}, Settings())
    return state


def test_rebase_checkpoints_full_saved_draft_and_installs_new_word(rebase):
    original = copy.deepcopy(rebase.draft)
    result = rebase.call()
    assert result['draft']['revision'] == 10 and result['draft']['blocks'] == rebase.fresh
    assert not result['source_changed'] and result['base_version']['id'] == str(UUID(int=6))
    assert rebase.events == ['project_lock', 'file_lock', 'latest_read', 'draft_lock']
    checkpoint = refinement.refinement_snapshot(actor(), UUID(int=3), UUID(int=4), result['snapshot']['sha256'], Settings())
    assert checkpoint['snapshot']['draft'] == vault._json_safe(original)
    assert rebase.audits[0]['snapshot']['git_sha'] == 'snapshot-commit'
    archive = rebase.commits[0]['manifest']['manuscript_draft_snapshot']
    assert json.loads(rebase.store.path_for(archive['object_key']).read_bytes()) == checkpoint['snapshot']


@pytest.mark.parametrize('changed', ['draft', 'source'])
def test_rebase_conflict_preserves_saved_blocks_and_creates_no_checkpoint(rebase, changed):
    if changed == 'draft':
        rebase.draft['revision'] += 1
    else:
        rebase.current = UUID(int=8)
    original = copy.deepcopy(rebase.draft)
    with pytest.raises(HTTPException) as error:
        rebase.call()
    assert error.value.status_code == 409 and rebase.draft == original
    assert not rebase.commits and not rebase.audits


def test_rebase_failure_rolls_back_checkpoint_and_draft_together(rebase):
    original = copy.deepcopy(rebase.draft)
    rebase.fail_update = True
    with pytest.raises(RuntimeError, match='injected'):
        rebase.call()
    assert rebase.draft == original and not rebase.commits and not rebase.audits


def test_rebase_permission_and_malformed_guards_fail_before_mutation(rebase):
    for arguments, status in [({'write': False}, 403), ({'expected_revision': True}, 422),
                              ({'expected_file_version_id': 'invalid'}, 422)]:
        with pytest.raises(HTTPException) as error:
            rebase.call(**arguments)
        assert error.value.status_code == status
    assert not rebase.commits and not rebase.events
