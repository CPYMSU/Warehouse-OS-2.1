from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.deps import ActorContext
from app.core.config import Settings
from app.services import research_semantic_refinement as service


def actor(*permissions):
    return ActorContext(user_id=UUID(int=1), tenant_id=UUID(int=2), tenant_slug="test",
                        tenant_name="Test", industry_template_key="research_lab", username="test",
                        display_name="Test", role_level=10, topology_level=10, topology_title="Test",
                        permissions=frozenset(permissions))


def anchor(block, quote=None, field="text"):
    source = block.get("latex", "") if field == "latex" else block["text"]
    quote = source if quote is None else quote
    start = source.index(quote)
    return {"block_id": block["id"], "field_name": field, "quote": quote,
            "start_offset": len(source[:start].encode("utf-16-le")) // 2,
            "end_offset": len(source[:start + len(quote)].encode("utf-16-le")) // 2,
            "offset_encoding": "utf16"}


class Result:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row


@pytest.fixture
def context(monkeypatch):
    state = SimpleNamespace(
        draft={"id": UUID(int=3), "project_id": UUID(int=4), "file_id": UUID(int=5), "revision": 7,
               "blocks": [{"id": "h", "type": "heading", "text": "A simple outcome model"},
                          {"id": "d", "type": "paragraph", "text": "Where X denotes units purchased and Y denotes total cost in dollars."},
                          {"id": "e", "type": "equation", "text": "𝑌 = 2𝑋 + 10", "latex": "Y = 2X + 10"},
                          {"id": "p", "type": "paragraph", "text": "The intercept is a fixed charge and the slope is a unit cost."}]},
        messages=[], calls=[], connection_calls=[],
    )

    class Session:
        def execute(self, statement, params):
            sql = " ".join(str(statement).split())
            assert params["tenant_id"] == UUID(int=2)
            assert params["draft_id"] == state.draft["id"]
            assert params["thread_id"] == UUID(int=6)
            if sql.startswith("SELECT"):
                needle = json.loads(params["needle"])[0]
                for message in reversed(state.messages):
                    if message["role"] == "assistant" and message["context_revision"] == params["revision"] and any(
                        citation.get("cache_key") == needle["cache_key"] for citation in message["citations"]
                    ):
                        return Result(copy.deepcopy(message))
                return Result()
            assert sql.startswith("INSERT INTO research.manuscript_agent_messages")
            state.messages.append({**params, "context_revision": params["revision"],
                                   "citations": json.loads(params["citations"]), "created_at": "2026-10-27T00:00:00Z"})
            return Result()

    @contextmanager
    def session(tenant_id):
        assert tenant_id == UUID(int=2)
        yield Session()

    def connection(*args, **kwargs):
        state.connection_calls.append(kwargs)
        return SimpleNamespace(model="test-fast")

    def completion(connection, **kwargs):
        state.calls.append(kwargs)
        return "## 一句話講清楚\n固定費用加單位成本。\n## 具體數字算一次\n教學假設，並非論文實證結果：X=3，Y=2×3+10=16美元。"

    monkeypatch.setattr(service, "tenant_session", session)
    monkeypatch.setattr(service, "_draft_target", lambda *args: ({"title": "Simple model"}, {"display_name": "paper.docx"}, state.draft))
    monkeypatch.setattr(service, "_thread", lambda *args: UUID(int=6))
    monkeypatch.setattr(service, "_connection", connection)
    monkeypatch.setattr(service, "chat_completion", completion)
    return state


def explain(state, **overrides):
    return service.defense_explanation(actor("research.write"), UUID(int=4), UUID(int=5),
        {"selection": anchor(state.draft["blocks"][2]), "expected_revision": state.draft["revision"], **overrides}, Settings())


def test_explanation_uses_one_fast_grounded_call_with_teaching_examples(context):
    result = explain(context)
    assert not result["cached"]
    assert len(context.calls) == 1 and context.connection_calls == [{"thinking": False}]
    call = context.calls[0]
    assert call["thinking"] is False and call["max_tokens"] <= 2400
    assert "教學假設，並非論文實證結果" in call["system_prompt"]
    assert "單位" in call["system_prompt"] and "量綱檢查" in call["system_prompt"]
    assert "30–60秒" in call["system_prompt"] and "不得捏造" in call["system_prompt"]
    assert "Y = 2X + 10" in call["user_prompt"] and "fixed charge" in call["user_prompt"]
    assert "units purchased" in call["user_prompt"]
    assert result["message"]["citations"][0]["purpose"] == "defense_explanation"
    assert result["selection"]["quote"] == "𝑌 = 2𝑋 + 10"
    assert [message["role"] for message in context.messages] == ["user", "assistant"]


def test_same_revision_selection_is_cached_without_extra_messages(context):
    first = explain(context)
    second = explain(context)
    assert second["cached"] and first["message"]["id"] == second["message"]["id"]
    assert len(context.calls) == 1 and len(context.messages) == 2
    context.draft["revision"] += 1
    assert not explain(context)["cached"]
    context.draft["blocks"][2]["latex"] = "Y = 3X + 10"
    assert not explain(context)["cached"]
    assert len(context.calls) == 3


def test_refresh_bypasses_only_matching_cache(context):
    explain(context)
    assert not explain(context, refresh=True)["cached"]
    assert len(context.calls) == 2


def test_late_formula_and_distant_single_letter_definitions_are_prioritized():
    blocks = [{"id": "b" + str(index), "type": "paragraph", "text": "Unrelated introduction. " * 160} for index in range(90)]
    blocks[4]["text"] = "Where X denotes units purchased and Y denotes total cost in dollars."
    blocks[84] = {"id": "section", "type": "heading", "text": "Late model interpretation"}
    blocks[87] = {"id": "formula", "type": "equation", "text": "Y = 2X + 10", "latex": "Y = 2X + 10"}
    selection = service._validated_defense_selection({"blocks": blocks}, anchor(blocks[87]))
    value, scope = service._defense_context(blocks, selection)
    assert "Y = 2X + 10" in value and "Late model interpretation" in value
    assert "units purchased" in value
    assert scope["truncated"] and "formula" in scope["included_block_ids"]
    assert len(value) < service.DEFENSE_CONTEXT_CHARACTERS + 1000


def test_utf16_and_latex_only_selections_are_exact_without_altering_legacy_validator():
    block = {"id": "math", "type": "equation", "text": "🙂 𝑌 = 2𝑋 + 10", "latex": "𝑌=2𝑋+10"}
    draft = {"blocks": [block]}
    chosen = service._validated_defense_selection(draft, anchor(block, "𝑌 = 2𝑋 + 10"))
    assert chosen["start_offset"] == 3 and chosen["quote"] == "𝑌 = 2𝑋 + 10"
    chosen = service._validated_defense_selection(draft, anchor(block, field="latex"))
    assert chosen["field_name"] == "latex" and chosen["quote"] == block["latex"]
    with pytest.raises(HTTPException) as error:
        service._validated_selection(draft, anchor(block, field="latex"))
    assert error.value.status_code == 422
    broken = {**anchor(block), "start_offset": 1}
    with pytest.raises(HTTPException) as error:
        service._validated_defense_selection(draft, broken)
    assert error.value.status_code == 422


def test_stale_selection_or_context_revision_is_rejected_before_model_call(context):
    for payload in ({"expected_revision": 6}, {"selection": {**anchor(context.draft["blocks"][2]), "quote": "old formula"}},
                    {"selection": {**anchor(context.draft["blocks"][2]), "source_sha256": "old hash"}}):
        with pytest.raises(HTTPException) as error:
            explain(context, **payload)
        assert error.value.status_code == 409
    assert not context.calls and not context.messages


def test_read_only_cannot_call_provider_or_create_messages(context):
    with pytest.raises(HTTPException) as error:
        service.defense_explanation(actor("research.read"), UUID(int=4), UUID(int=5), {}, Settings())
    assert error.value.status_code == 403
    assert not context.calls and not context.messages


def test_malformed_requests_do_not_reach_provider(context):
    for payload in ({"refresh": "false"}, {"expected_revision": True}, {"selection": None}):
        with pytest.raises(HTTPException) as error:
            explain(context, **payload)
        assert error.value.status_code == 422
    assert not context.calls
