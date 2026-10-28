from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

from app.services import research_semantic_refinement as service


def test_translation_coverage_uses_current_hash_and_nonempty_translation():
    blocks = [
        {"id": "p", "type": "paragraph", "text": "Current words"},
        {"id": "t", "type": "table_row", "cells": ["", "Table value"]},
        {"id": "image", "type": "image", "text": ""},
        {"id": "formula", "type": "equation", "text": "  "},
    ]
    artifacts = [
        {"block_id": "p", "artifact_kind": "block_semantics", "source_sha256": service._block_hash(blocks[0]), "content": {"translation_zh_cn": "譯文"}},
        {"block_id": "t", "artifact_kind": "block_semantics", "source_sha256": service._block_hash(blocks[1]), "content": {"translation_zh_cn": "  "}},
        {"block_id": "p", "artifact_kind": "block_semantics", "source_sha256": "old", "content": {"translation_zh_cn": "舊文"}},
    ]
    assert service._translation_coverage(blocks, artifacts) == {"total": 2, "translated": 1, "missing_count": 1}
    assert service._semantic_content_complete({"translation_zh_cn": "已譯", "distillation": ""}, {"translate"})
    assert not service._semantic_content_complete({"translation_zh_cn": "已譯", "distillation": ""}, {"translate", "distill"})


def test_partial_batches_are_saved_retried_only_when_needed_and_duplicate_claim_skips(monkeypatch):
    actor = SimpleNamespace(tenant_id=UUID(int=1))
    run_id, draft_id, project_id, file_id = (UUID(int=i) for i in (2, 3, 4, 5))
    blocks = [{"id": str(i), "type": "paragraph", "text": "English " + str(i)} for i in range(16)]
    draft = {"id": draft_id, "project_id": project_id, "file_id": file_id, "revision": 2, "blocks": blocks}
    run = {"draft_id": draft_id, "source_revision": 2, "modes": ["translate"], "block_ids": []}
    state = {"status": "queued", "stored": {}, "calls": [], "result": None}
    state["stored"]["0"] = {"translation_zh_cn": "已有譯文", "distillation": "舊蒸餾"}

    class Result:
        def __init__(self, row=None): self.row = row
        def scalar_one_or_none(self): return self.row
        def mappings(self): return self
        def one(self): return self.row

    class Session:
        def execute(self, statement, params):
            sql = str(statement)
            if "status='processing'" in sql:
                if state["status"] not in {"queued", "failed"}: return Result()
                state["status"] = "processing"
                return Result(run_id)
            if "SELECT * FROM research.manuscript_drafts" in sql:
                return Result(draft)
            if "SET status='ready'" in sql:
                state["status"] = "ready"
                state["result"] = params["result"]
            if "SET status='failed'" in sql:
                state["status"] = "failed"
                state["result"] = params["result"]
            return Result()

    @contextmanager
    def session(*args, **kwargs): yield Session()
    monkeypatch.setattr(service, "tenant_session", session)
    monkeypatch.setattr(service, "_run_row", lambda *args: run)
    monkeypatch.setattr(service, "_connection", lambda *args: SimpleNamespace(model="test"))
    monkeypatch.setattr(service, "_existing_hashes", lambda actor, draft, modes: {
        (item["id"], service._block_hash(item)) for item in blocks
        if service._semantic_content_complete(state["stored"].get(item["id"]), modes)
    })
    def store(actor, draft, **artifact):
        current = state["stored"].setdefault(artifact["block_id"], {})
        current.update({k: v for k, v in artifact["content"].items() if not isinstance(v, str) or v.strip()})
    monkeypatch.setattr(service, "_store_artifact", store)
    def batch(connection, batch_blocks):
        ids = [block["id"] for block in batch_blocks]
        state["calls"].append(ids)
        if ids == ["15"] and state["calls"].count(ids) == 1:
            raise RuntimeError("temporary provider error")
        return [{"block_id": item["id"], "source_sha256": service._block_hash(item),
                 "content": {"translation_zh_cn": "翻譯 " + item["id"], "distillation": ""}} for item in batch_blocks]
    monkeypatch.setattr(service, "_semantic_batch", batch)
    result = service.run_semantic_ai(actor, run_id, None)
    assert result["status"] == "ready" and result["missing_count"] == 0
    assert len(state["stored"]) == 16 and state["stored"]["0"]["distillation"] == "舊蒸餾"
    assert state["calls"].count(["15"]) == 2
    assert all("0" not in ids for ids in state["calls"])
    assert service.run_semantic_ai(actor, run_id, None) == {"status": "already_claimed"}
    # A permanently omitted block leaves the other 15 saved, is tried at most
    # twice, and cannot be reported as a fully completed run.
    del state["stored"]["15"]
    state["status"] = "queued"
    state["calls"].clear()
    def omitted(connection, batch_blocks):
        state["calls"].append([item["id"] for item in batch_blocks])
        return []
    monkeypatch.setattr(service, "_semantic_batch", omitted)
    partial = service.run_semantic_ai(actor, run_id, None)
    assert partial["status"] == "failed" and partial["missing_count"] == 1
    assert state["calls"] == [["15"], ["15"]] and len(state["stored"]) == 15


def test_outdated_queued_run_does_not_call_provider(monkeypatch):
    actor = SimpleNamespace(tenant_id=UUID(int=1))
    run = {"draft_id": UUID(int=3), "source_revision": 1, "modes": ["translate"], "block_ids": []}
    state = {"failed": False}
    class Result:
        def __init__(self, row=None): self.row = row
        def scalar_one_or_none(self): return self.row
        def mappings(self): return self
        def one(self): return self.row
    class Session:
        def execute(self, statement, params):
            sql = str(statement)
            if "status='processing'" in sql: return Result(UUID(int=2))
            if "SELECT * FROM research.manuscript_drafts" in sql: return Result({"id": UUID(int=3), "revision": 2, "blocks": []})
            if "status='failed'" in sql: state["failed"] = True
            return Result()
    @contextmanager
    def session(*args, **kwargs): yield Session()
    monkeypatch.setattr(service, "tenant_session", session)
    monkeypatch.setattr(service, "_run_row", lambda *args: run)
    monkeypatch.setattr(service, "_connection", lambda *args: (_ for _ in ()).throw(AssertionError("provider was called")))
    result = service.run_semantic_ai(actor, UUID(int=2), None)
    assert result["status"] == "failed" and state["failed"]
