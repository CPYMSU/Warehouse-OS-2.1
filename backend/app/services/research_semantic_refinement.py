"""Paragraph-aligned translation, distillation, and parallel manuscript reviewers."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.db.session import tenant_session
from app.services.integrations import (
    DEEPSEEK_RUNTIME_MODELS,
    ModelConnection,
    chat_completion,
    connected_deepseek,
)
from app.services.research_review import _target_rows

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings


MAX_CONTEXT_CHARACTERS = 52_000
MAX_BATCH_CHARACTERS = 10_000
MAX_BATCH_BLOCKS = 14
MAX_PARALLEL_CALLS = 4
DOCUMENT_BLOCK_ID = "__document__"
SEMANTIC_MODES = frozenset({"translate", "distill"})
AGENT_TYPES = frozenset({"neutrality", "logic", "clarity", "professional", "chief"})
AGENT_LABELS = {
    "neutrality": "用词中立化评审",
    "logic": "整体逻辑衔接评审",
    "clarity": "表达具体易懂评审",
    "professional": "内容专业化评审",
    "chief": "主 AI 总编辑",
}
AGENT_INSTRUCTIONS = {
    "neutrality": (
        "检查绝对化、宣传性、情绪性、带立场和证据不足的措辞。不要机械弱化有充分证据的结论。"
    ),
    "logic": (
        "检查段落和章节之间的前提、过渡、论证顺序、重复、跳跃，以及方法、结果和结论是否衔接。"
    ),
    "clarity": (
        "检查模糊指代、抽象空话、长句、概念未定义和读者理解障碍，使表达具体而不牺牲准确性。"
    ),
    "professional": (
        "检查专业术语、研究方法、统计表达、公式、图表、引文和结论边界。蒸馏只用于定位，判断必须引用原始区块。"
    ),
    "chief": (
        "综合全文、用户决策和其他评审的结论；识别冲突并解释取舍，不得把未确认建议直接改入正文。"
    ),
}


def _require_write(actor: ActorContext) -> None:
    if "research.write" not in actor.permissions:
        raise HTTPException(status_code=403, detail="Research write permission denied")


def _json(value: object) -> object:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _blocks(value: object) -> list[dict[str, object]]:
    parsed = _json(value)
    return [dict(item) for item in parsed] if isinstance(parsed, list) else []


def _block_source(block: dict[str, object]) -> str:
    cells = block.get("cells") if isinstance(block.get("cells"), list) else []
    return json.dumps(
        {
            "type": str(block.get("type") or "paragraph"),
            "text": str(block.get("text") or ""),
            "cells": [str(item or "") for item in cells],
            "level": block.get("level"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _block_hash(block: dict[str, object]) -> str:
    return hashlib.sha256(_block_source(block).encode()).hexdigest()


def _document_hash(blocks: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for block in blocks:
        digest.update(str(block.get("id") or "").encode())
        digest.update(b"\x00")
        digest.update(_block_hash(block).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _validated_selection(
    draft: dict[str, object],
    raw_selection: object,
) -> dict[str, object]:
    selection = _json(raw_selection)
    if not isinstance(selection, dict):
        raise HTTPException(status_code=422, detail="selection must be an object")
    block_id = str(selection.get("block_id") or "").strip()
    block = next(
        (
            item
            for item in _blocks(draft.get("blocks"))
            if str(item.get("id") or "") == block_id
        ),
        None,
    )
    if block is None:
        raise HTTPException(status_code=409, detail="Selected manuscript block no longer exists")
    field_name = str(selection.get("field_name") or "text").strip().lower()
    cell_index: int | None = None
    if field_name == "cell":
        try:
            cell_index = int(selection.get("cell_index"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="cell_index is required") from None
        cells = block.get("cells") if isinstance(block.get("cells"), list) else []
        if cell_index < 0 or cell_index >= len(cells):
            raise HTTPException(status_code=409, detail="Selected table cell no longer exists")
        source = str(cells[cell_index] or "")
    elif field_name == "text":
        source = str(block.get("text") or "")
    else:
        raise HTTPException(status_code=422, detail="Unsupported selection field")
    try:
        start = int(selection.get("start_offset"))
        end = int(selection.get("end_offset"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="selection offsets are required") from None
    if start < 0 or end <= start or end > len(source) or end - start > 12_000:
        raise HTTPException(status_code=422, detail="selection offsets are invalid")
    quote = source[start:end]
    supplied_quote = str(selection.get("quote") or "")
    if not quote.strip() or (supplied_quote and supplied_quote != quote):
        raise HTTPException(status_code=409, detail="Selected manuscript text has changed")
    supplied_hash = str(selection.get("source_sha256") or "")
    source_sha256 = _block_hash(block)
    if supplied_hash and supplied_hash != source_sha256:
        raise HTTPException(status_code=409, detail="Selected manuscript block has changed")
    return {
        "block_id": block_id,
        "field_name": field_name,
        "cell_index": cell_index,
        "start_offset": start,
        "end_offset": end,
        "quote": quote,
        "prefix": source[max(0, start - 240) : start],
        "suffix": source[end : end + 240],
        "source_sha256": source_sha256,
    }


def _draft_target(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    project, file_row, _version = _target_rows(actor, project_ref, file_ref, None)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text("SELECT * FROM research.manuscript_drafts WHERE file_id=:file_id"),
                {"file_id": file_row["id"]},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Start manuscript refinement first")
    return dict(project), dict(file_row), dict(row)


def _run_row(actor: ActorContext, run_id: UUID) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text("SELECT * FROM research.manuscript_ai_runs WHERE id=:id"),
                {"id": run_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Manuscript AI run not found")
    return dict(row)


def _parse_model_json(value: str) -> dict[str, object]:
    candidate = value.strip()
    if candidate.startswith("```"):
        first_break = candidate.find("\n")
        candidate = candidate[first_break + 1 :] if first_break >= 0 else candidate
        if candidate.rstrip().endswith("```"):
            candidate = candidate.rstrip()[:-3]
    payload = json.loads(candidate.strip())
    if not isinstance(payload, dict):
        raise ValueError("AI response must be a JSON object")
    return payload


def _artifact_rows(
    actor: ActorContext,
    draft_id: object,
) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT DISTINCT ON (block_id, artifact_kind, locale)
                           id, block_id, artifact_kind, locale, source_sha256,
                           source_revision, content, model, updated_at
                    FROM research.manuscript_artifacts
                    WHERE draft_id=:draft_id
                    ORDER BY block_id, artifact_kind, locale, updated_at DESC
                    """
                ),
                {"draft_id": draft_id},
            )
            .mappings()
            .all()
        )
    result: list[dict[str, object]] = []
    for raw in rows:
        item = dict(raw)
        item["id"] = str(item["id"])
        item["content"] = _json(item.get("content")) or {}
        item["updated_at"] = str(item["updated_at"])
        result.append(item)
    return result


def _thread_rows(actor: ActorContext, draft_id: object) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT t.*,
                      COALESCE((
                        SELECT jsonb_agg(jsonb_build_object(
                          'id', m.id, 'role', m.role, 'body', m.body,
                          'citations', m.citations, 'context_revision', m.context_revision,
                          'model', m.model, 'created_at', m.created_at
                        ) ORDER BY m.created_at)
                        FROM research.manuscript_agent_messages m
                        WHERE m.thread_id=t.id
                      ), '[]'::jsonb) AS messages
                    FROM research.manuscript_agent_threads t
                    WHERE t.draft_id=:draft_id AND t.status='active'
                    ORDER BY CASE t.agent_type
                      WHEN 'neutrality' THEN 1 WHEN 'logic' THEN 2
                      WHEN 'clarity' THEN 3 WHEN 'professional' THEN 4 ELSE 5 END
                    """
                ),
                {"draft_id": draft_id},
            )
            .mappings()
            .all()
        )
    result: list[dict[str, object]] = []
    for raw in rows:
        item = dict(raw)
        item["id"] = str(item["id"])
        item["draft_id"] = str(item["draft_id"])
        item["scope"] = _json(item.get("scope")) or {}
        item["messages"] = _json(item.get("messages")) or []
        item["created_at"] = str(item["created_at"])
        item["updated_at"] = str(item["updated_at"])
        result.append(item)
    return result


def _finding_rows(
    actor: ActorContext,
    draft_id: object,
    current_blocks: list[dict[str, object]],
) -> list[dict[str, object]]:
    hashes = {str(item.get("id") or ""): _block_hash(item) for item in current_blocks}
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT * FROM research.manuscript_findings
                    WHERE draft_id=:draft_id
                    ORDER BY CASE status WHEN 'open' THEN 0 ELSE 1 END,
                             created_at DESC LIMIT 300
                    """
                ),
                {"draft_id": draft_id},
            )
            .mappings()
            .all()
        )
    result: list[dict[str, object]] = []
    for raw in rows:
        item = dict(raw)
        if item["status"] == "open" and hashes.get(str(item["block_id"])) != str(
            item["source_sha256"]
        ):
            item["status"] = "stale"
        for key in ("id", "draft_id", "thread_id", "run_id"):
            if item.get(key) is not None:
                item[key] = str(item[key])
        item["evidence"] = _json(item.get("evidence")) or []
        item["confidence"] = float(item["confidence"]) if item.get("confidence") else None
        item["created_at"] = str(item["created_at"])
        item["updated_at"] = str(item["updated_at"])
        result.append(item)
    return result


def _annotation_rows(
    actor: ActorContext,
    draft: dict[str, object],
) -> list[dict[str, object]]:
    blocks = {
        str(item.get("id") or ""): item for item in _blocks(draft.get("blocks"))
    }
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT a.*, u.display_name AS author_name
                    FROM research.manuscript_annotations a
                    LEFT JOIN iam.users u ON u.id=a.created_by
                    WHERE a.draft_id=:draft_id
                    ORDER BY CASE a.status WHEN 'open' THEN 0 ELSE 1 END,
                             a.created_at DESC
                    LIMIT 300
                    """
                ),
                {"draft_id": draft["id"]},
            )
            .mappings()
            .all()
        )
    result: list[dict[str, object]] = []
    for raw in rows:
        item = dict(raw)
        block = blocks.get(str(item["block_id"]))
        if block is None or _block_hash(block) != str(item["source_sha256"]):
            item["status"] = "stale"
        for key in ("id", "draft_id", "created_by", "resolved_by"):
            if item.get(key) is not None:
                item[key] = str(item[key])
        for key in ("created_at", "updated_at", "resolved_at"):
            item[key] = str(item[key]) if item.get(key) else None
        result.append(item)
    return result


def create_manuscript_annotation(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_write(actor)
    project, file_row, draft = _draft_target(actor, project_ref, file_ref)
    selection = _validated_selection(draft, payload.get("selection"))
    annotation_type = str(payload.get("annotation_type") or "note").strip().lower()
    if annotation_type not in {"highlight", "note"}:
        raise HTTPException(status_code=422, detail="Unsupported annotation type")
    color = str(payload.get("color") or "yellow").strip().lower()
    if color not in {"yellow", "mint", "blue", "rose"}:
        raise HTTPException(status_code=422, detail="Unsupported annotation color")
    body = str(payload.get("body") or "").strip()
    if len(body) > 20_000 or (annotation_type == "note" and not body):
        raise HTTPException(
            status_code=422,
            detail="note body must contain 1–20000 characters",
        )
    annotation_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.manuscript_annotations(
                      id, tenant_id, project_id, file_id, draft_id, block_id,
                      source_sha256, field_name, cell_index, start_offset, end_offset,
                      quote, prefix, suffix, annotation_type, color, body, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :file_id, :draft_id, :block_id,
                      :source_sha256, :field_name, :cell_index, :start_offset, :end_offset,
                      :quote, :prefix, :suffix, :annotation_type, :color, :body, :created_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": annotation_id,
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "file_id": file_row["id"],
                    "draft_id": draft["id"],
                    **selection,
                    "annotation_type": annotation_type,
                    "color": color,
                    "body": body,
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
    item = dict(row)
    for key in ("id", "draft_id", "created_by", "resolved_by"):
        if item.get(key) is not None:
            item[key] = str(item[key])
    for key in ("created_at", "updated_at", "resolved_at"):
        item[key] = str(item[key]) if item.get(key) else None
    return {"ok": True, "annotation": item}


def set_manuscript_annotation_status(
    actor: ActorContext,
    annotation_id: object,
    *,
    resolved: bool,
) -> dict[str, object]:
    _require_write(actor)
    try:
        parsed_id = UUID(str(annotation_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="Manuscript annotation not found") from None
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    UPDATE research.manuscript_annotations
                    SET status=:status, resolved_by=:resolved_by,
                        resolved_at=CASE WHEN :resolved THEN now() ELSE NULL END,
                        updated_at=now()
                    WHERE id=:id
                    RETURNING *
                    """
                ),
                {
                    "id": parsed_id,
                    "status": "resolved" if resolved else "open",
                    "resolved_by": actor.user_id if resolved else None,
                    "resolved": resolved,
                },
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Manuscript annotation not found")
    return {
        "ok": True,
        "annotation_id": str(parsed_id),
        "status": str(row["status"]),
    }


def semantic_workspace(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
) -> dict[str, object]:
    _require_write(actor)
    project, file_row, draft = _draft_target(actor, project_ref, file_ref)
    blocks = _blocks(draft.get("blocks"))
    artifacts = _artifact_rows(actor, draft["id"])
    current_hashes = {str(item.get("id") or ""): _block_hash(item) for item in blocks}
    current_hashes[DOCUMENT_BLOCK_ID] = _document_hash(blocks)
    for artifact in artifacts:
        artifact["stale"] = current_hashes.get(str(artifact["block_id"])) != str(
            artifact["source_sha256"]
        )
    with tenant_session(actor.tenant_id) as session:
        latest_run = (
            session.execute(
                text(
                    "SELECT * FROM research.manuscript_ai_runs "
                    "WHERE draft_id=:draft_id ORDER BY created_at DESC LIMIT 1"
                ),
                {"draft_id": draft["id"]},
            )
            .mappings()
            .one_or_none()
        )
    run = dict(latest_run) if latest_run else None
    if run:
        for key in ("id", "draft_id"):
            run[key] = str(run[key])
        run["modes"] = _json(run.get("modes")) or []
        run["block_ids"] = _json(run.get("block_ids")) or []
        run["result"] = _json(run.get("result")) or {}
        for key in ("created_at", "updated_at", "started_at", "finished_at"):
            run[key] = str(run[key]) if run.get(key) else None
    return {
        "source": "research_semantic_refinement",
        "project": {"id": str(project["id"]), "title": project["title"]},
        "file": {"id": str(file_row["id"]), "display_name": file_row["display_name"]},
        "draft": {"id": str(draft["id"]), "revision": int(draft["revision"])},
        "latest_run": run,
        "artifacts": artifacts,
        "threads": _thread_rows(actor, draft["id"]),
        "findings": _finding_rows(actor, draft["id"], blocks),
        "annotations": _annotation_rows(actor, draft),
        "agents": [
            {"type": key, "label": AGENT_LABELS[key], "independent": key != "chief"}
            for key in ("neutrality", "logic", "clarity", "professional", "chief")
        ],
        "capabilities": {
            "paragraph_translation_zh_cn": True,
            "visible_distillation": True,
            "parallel_reviewers": True,
            "chief_context_bus": True,
            "dedicated_runtime_required": False,
            "incremental_by_content_hash": True,
            "draft_selection_annotations": True,
            "selection_grounded_ai": True,
        },
    }


def queue_semantic_run(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_write(actor)
    project, file_row, draft = _draft_target(actor, project_ref, file_ref)
    raw_modes = payload.get("modes") or ["translate", "distill"]
    if not isinstance(raw_modes, list):
        raise HTTPException(status_code=422, detail="modes must be an array")
    modes = [str(item).strip().lower() for item in raw_modes]
    allowed = SEMANTIC_MODES | {f"review:{item}" for item in AGENT_TYPES if item != "chief"}
    if not modes or any(item not in allowed for item in modes):
        raise HTTPException(status_code=422, detail="Unsupported manuscript AI mode")
    raw_block_ids = payload.get("block_ids") or []
    if not isinstance(raw_block_ids, list):
        raise HTTPException(status_code=422, detail="block_ids must be an array")
    valid_ids = {str(item.get("id") or "") for item in _blocks(draft.get("blocks"))}
    block_ids = sorted(
        {str(item).strip() for item in raw_block_ids if str(item).strip() in valid_ids}
    )
    with tenant_session(actor.tenant_id) as session:
        active = (
            session.execute(
                text(
                    """
                    SELECT * FROM research.manuscript_ai_runs
                    WHERE draft_id=:draft_id AND status IN ('queued','processing')
                      AND source_revision=:revision
                      AND modes=CAST(:modes AS jsonb) AND block_ids=CAST(:block_ids AS jsonb)
                    ORDER BY created_at DESC LIMIT 1
                    """
                ),
                {
                    "draft_id": draft["id"],
                    "revision": int(draft["revision"]),
                    "modes": json.dumps(modes),
                    "block_ids": json.dumps(block_ids),
                },
            )
            .mappings()
            .one_or_none()
        )
        if active is not None:
            return {"accepted": True, "run_id": str(active["id"]), "status": active["status"]}
        run_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO research.manuscript_ai_runs(
                  id, tenant_id, project_id, file_id, draft_id, source_revision,
                  modes, block_ids, requested_by
                ) VALUES (
                  :id, :tenant_id, :project_id, :file_id, :draft_id, :source_revision,
                  CAST(:modes AS jsonb), CAST(:block_ids AS jsonb), :requested_by
                )
                """
            ),
            {
                "id": run_id,
                "tenant_id": actor.tenant_id,
                "project_id": project["id"],
                "file_id": file_row["id"],
                "draft_id": draft["id"],
                "source_revision": int(draft["revision"]),
                "modes": json.dumps(modes),
                "block_ids": json.dumps(block_ids),
                "requested_by": actor.user_id,
            },
        )
    return {"accepted": True, "run_id": str(run_id), "status": "queued", "modes": modes}


def _connection(
    actor: ActorContext,
    settings: Settings,
    *,
    thinking: bool = False,
) -> ModelConnection:
    connected = connected_deepseek(actor, settings)
    return ModelConnection(
        base_url=connected.base_url,
        model=DEEPSEEK_RUNTIME_MODELS["thinking" if thinking else "balanced"],
        api_key=connected.api_key,
    )


def _batches(blocks: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    result: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    size = 0
    for block in blocks:
        value_size = len(_block_source(block))
        if current and (
            len(current) >= MAX_BATCH_BLOCKS
            or size + value_size > MAX_BATCH_CHARACTERS
        ):
            result.append(current)
            current = []
            size = 0
        current.append(block)
        size += value_size
    if current:
        result.append(current)
    return result


def _semantic_batch(
    connection: ModelConnection,
    blocks: list[dict[str, object]],
) -> list[dict[str, object]]:
    source = [
        {
            "block_id": str(item.get("id") or ""),
            "type": str(item.get("type") or "paragraph"),
            "text": str(item.get("text") or ""),
            "cells": item.get("cells") if isinstance(item.get("cells"), list) else [],
        }
        for item in blocks
    ]
    response = chat_completion(
        connection,
        system_prompt=(
            "你是科研论文的段落语义处理器。逐项输出简体中文翻译和忠实蒸馏，不补造事实。"
            "公式本身、数字、单位、DOI、引文编号和图表编号必须保留。"
            "输出 JSON 对象，items 数组每项必须含 block_id、translation_zh_cn、distillation、"
            "argument_role、keywords。输入已经是简体中文时 translation_zh_cn 保持准确原意。"
        ),
        user_prompt=json.dumps(source, ensure_ascii=False),
        thinking=False,
        max_tokens=4_000,
        json_mode=True,
    )
    payload = _parse_model_json(response)
    by_id = {str(item.get("id") or ""): item for item in blocks}
    results: list[dict[str, object]] = []
    for raw in payload.get("items") or []:
        if not isinstance(raw, dict):
            continue
        block_id = str(raw.get("block_id") or "")
        if block_id not in by_id:
            continue
        results.append(
            {
                "block_id": block_id,
                "source_sha256": _block_hash(by_id[block_id]),
                "content": {
                    "translation_zh_cn": str(raw.get("translation_zh_cn") or "")[:120_000],
                    "distillation": str(raw.get("distillation") or "")[:20_000],
                    "argument_role": str(raw.get("argument_role") or "")[:500],
                    "keywords": [str(item)[:200] for item in raw.get("keywords") or []][:20],
                },
            }
        )
    return results


def _store_artifact(
    actor: ActorContext,
    draft: dict[str, object],
    *,
    block_id: str,
    artifact_kind: str,
    source_sha256: str,
    content: dict[str, object],
    model: str,
) -> None:
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO research.manuscript_artifacts(
                  id, tenant_id, project_id, file_id, draft_id, block_id,
                  artifact_kind, source_sha256, source_revision, content, model
                ) VALUES (
                  :id, :tenant_id, :project_id, :file_id, :draft_id, :block_id,
                  :artifact_kind, :source_sha256, :source_revision,
                  CAST(:content AS jsonb), :model
                ) ON CONFLICT (
                  tenant_id, draft_id, block_id, artifact_kind, source_sha256, locale
                ) DO UPDATE SET content=EXCLUDED.content, source_revision=EXCLUDED.source_revision,
                  model=EXCLUDED.model, updated_at=now()
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "project_id": draft["project_id"],
                "file_id": draft["file_id"],
                "draft_id": draft["id"],
                "block_id": block_id,
                "artifact_kind": artifact_kind,
                "source_sha256": source_sha256,
                "source_revision": int(draft["revision"]),
                "content": json.dumps(content, ensure_ascii=False),
                "model": model,
            },
        )


def _existing_hashes(actor: ActorContext, draft_id: object) -> set[tuple[str, str]]:
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            text(
                "SELECT block_id,source_sha256 FROM research.manuscript_artifacts "
                "WHERE draft_id=:draft_id AND artifact_kind='block_semantics'"
            ),
            {"draft_id": draft_id},
        ).all()
    return {(str(row[0]), str(row[1])) for row in rows}


def _document_digest(
    actor: ActorContext,
    draft: dict[str, object],
    blocks: list[dict[str, object]],
    connection: ModelConnection,
) -> bool:
    source_sha = _document_hash(blocks)
    with tenant_session(actor.tenant_id) as session:
        exists = session.execute(
            text(
                """
                SELECT 1 FROM research.manuscript_artifacts
                WHERE draft_id=:draft_id AND block_id=:block_id
                  AND artifact_kind='document_digest' AND source_sha256=:sha
                """
            ),
            {"draft_id": draft["id"], "block_id": DOCUMENT_BLOCK_ID, "sha": source_sha},
        ).scalar_one_or_none()
    if exists:
        return False
    lines: list[str] = []
    used = 0
    for index, block in enumerate(blocks):
        line = f"[{block.get('id')}] {block.get('type')}\n{block.get('text') or ''}"
        if used + len(line) > MAX_CONTEXT_CHARACTERS:
            break
        lines.append(line)
        used += len(line)
    response = chat_completion(
        connection,
        system_prompt=(
            "你是论文语义孪生总索引员。只根据原始区块建立可见的全文蒸馏资源。"
            "输出 JSON，包含 summary、research_question、method、findings、limitations、"
            "argument_outline、glossary。argument_outline 和 glossary 为数组；不得补造事实。"
        ),
        user_prompt="\n\n".join(lines),
        thinking=False,
        max_tokens=3_600,
        json_mode=True,
    )
    payload = _parse_model_json(response)
    content = {
        "summary": str(payload.get("summary") or "")[:20_000],
        "research_question": str(payload.get("research_question") or "")[:5_000],
        "method": str(payload.get("method") or "")[:10_000],
        "findings": str(payload.get("findings") or "")[:10_000],
        "limitations": str(payload.get("limitations") or "")[:10_000],
        "argument_outline": payload.get("argument_outline")
        if isinstance(payload.get("argument_outline"), list)
        else [],
        "glossary": payload.get("glossary") if isinstance(payload.get("glossary"), list) else [],
    }
    _store_artifact(
        actor,
        draft,
        block_id=DOCUMENT_BLOCK_ID,
        artifact_kind="document_digest",
        source_sha256=source_sha,
        content=content,
        model=connection.model,
    )
    return True


def _thread(actor: ActorContext, draft: dict[str, object], agent_type: str) -> UUID:
    with tenant_session(actor.tenant_id) as session:
        value = session.execute(
            text(
                """
                INSERT INTO research.manuscript_agent_threads(
                  id, tenant_id, project_id, file_id, draft_id,
                  agent_type, title, created_by
                ) VALUES (
                  :id, :tenant_id, :project_id, :file_id, :draft_id,
                  :agent_type, :title, :created_by
                ) ON CONFLICT (tenant_id, draft_id, agent_type)
                DO UPDATE SET status='active', updated_at=now()
                RETURNING id
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "project_id": draft["project_id"],
                "file_id": draft["file_id"],
                "draft_id": draft["id"],
                "agent_type": agent_type,
                "title": AGENT_LABELS[agent_type],
                "created_by": actor.user_id,
            },
        ).scalar_one()
    return UUID(str(value))


def _review_context(
    actor: ActorContext,
    draft: dict[str, object],
    blocks: list[dict[str, object]],
    *,
    include_findings: bool,
) -> str:
    artifacts = _artifact_rows(actor, draft["id"])
    current = {
        (str(item["block_id"]), str(item["source_sha256"])): item
        for item in artifacts
        if not item.get("stale")
    }
    parts: list[str] = []
    document = next(
        (
            item
            for item in artifacts
            if item["block_id"] == DOCUMENT_BLOCK_ID
            and item["source_sha256"] == _document_hash(blocks)
        ),
        None,
    )
    if document:
        parts.append("【全文蒸馏导航】\n" + json.dumps(document["content"], ensure_ascii=False))
    for block in blocks:
        block_id = str(block.get("id") or "")
        semantic = current.get((block_id, _block_hash(block)))
        value = f"【原始区块 {block_id} · {block.get('type')}】\n{block.get('text') or ''}"
        if semantic:
            value += "\n【段落蒸馏】\n" + str(
                (semantic.get("content") or {}).get("distillation") or ""
            )
        if sum(len(item) for item in parts) + len(value) > MAX_CONTEXT_CHARACTERS:
            break
        parts.append(value)
    if include_findings:
        findings = _finding_rows(actor, draft["id"], blocks)
        concise = [
            {
                "agent": item["agent_type"],
                "block_id": item["block_id"],
                "status": item["status"],
                "rationale": item["rationale"],
                "suggestion": item["suggestion"],
            }
            for item in findings[:80]
        ]
        parts.append("【其他评审与用户决策】\n" + json.dumps(concise, ensure_ascii=False))
    return "\n\n".join(parts)


def _review_agent(
    actor: ActorContext,
    draft: dict[str, object],
    blocks: list[dict[str, object]],
    agent_type: str,
    run_id: UUID,
    settings: Settings,
) -> int:
    connection = _connection(actor, settings, thinking=agent_type == "professional")
    thread_id = _thread(actor, draft, agent_type)
    context = _review_context(actor, draft, blocks, include_findings=False)
    response = chat_completion(
        connection,
        system_prompt=(
            f"你是{AGENT_LABELS[agent_type]}。{AGENT_INSTRUCTIONS[agent_type]}"
            "输出 JSON：summary 为本轮总评；findings 为数组。每项必须含 block_id、severity、"
            "category、quote、rationale、suggestion、evidence、confidence。"
            "suggestion 必须是可替换该区块的完整文本；不需要修改则不要生成 finding。"
            "只能引用输入中存在的原始区块 ID。"
        ),
        user_prompt=context,
        thinking=agent_type == "professional",
        max_tokens=4_000,
        json_mode=True,
    )
    payload = _parse_model_json(response)
    by_id = {str(item.get("id") or ""): item for item in blocks}
    summary = str(payload.get("summary") or "评审完成")[:30_000]
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO research.manuscript_agent_messages(
                  id, tenant_id, project_id, file_id, draft_id, thread_id,
                  role, body, context_revision, model, created_by
                ) VALUES (
                  :id, :tenant_id, :project_id, :file_id, :draft_id, :thread_id,
                  'assistant', :body, :revision, :model, :created_by
                )
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "project_id": draft["project_id"],
                "file_id": draft["file_id"],
                "draft_id": draft["id"],
                "thread_id": thread_id,
                "body": summary,
                "revision": int(draft["revision"]),
                "model": connection.model,
                "created_by": actor.user_id,
            },
        )
        count = 0
        for raw in payload.get("findings") or []:
            if not isinstance(raw, dict):
                continue
            block_id = str(raw.get("block_id") or "")
            block = by_id.get(block_id)
            rationale = str(raw.get("rationale") or "").strip()
            if block is None or not rationale:
                continue
            severity = str(raw.get("severity") or "medium").lower()
            if severity not in {"low", "medium", "high"}:
                severity = "medium"
            try:
                confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.7))))
            except (TypeError, ValueError):
                confidence = 0.7
            evidence = raw.get("evidence") if isinstance(raw.get("evidence"), list) else []
            session.execute(
                text(
                    """
                    INSERT INTO research.manuscript_findings(
                      id, tenant_id, project_id, file_id, draft_id, thread_id, run_id,
                      agent_type, block_id, source_sha256, base_revision, severity,
                      category, quote, rationale, suggestion, evidence, confidence
                    ) VALUES (
                      :id, :tenant_id, :project_id, :file_id, :draft_id, :thread_id, :run_id,
                      :agent_type, :block_id, :source_sha256, :base_revision, :severity,
                      :category, :quote, :rationale, :suggestion,
                      CAST(:evidence AS jsonb), :confidence
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": draft["project_id"],
                    "file_id": draft["file_id"],
                    "draft_id": draft["id"],
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "agent_type": agent_type,
                    "block_id": block_id,
                    "source_sha256": _block_hash(block),
                    "base_revision": int(draft["revision"]),
                    "severity": severity,
                    "category": str(raw.get("category") or "")[:300],
                    "quote": str(raw.get("quote") or "")[:12_000],
                    "rationale": rationale[:30_000],
                    "suggestion": str(raw.get("suggestion") or "")[:120_000],
                    "evidence": json.dumps(evidence[:30], ensure_ascii=False),
                    "confidence": confidence,
                },
            )
            count += 1
    return count


def run_semantic_ai(
    actor: ActorContext,
    run_id: object,
    settings: Settings,
) -> dict[str, object]:
    parsed_id = UUID(str(run_id))
    run = _run_row(actor, parsed_id)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                "UPDATE research.manuscript_ai_runs SET status='processing', "
                "started_at=now(), error=NULL WHERE id=:id AND status IN ('queued','failed')"
            ),
            {"id": parsed_id},
        )
        draft_row = (
            session.execute(
                text("SELECT * FROM research.manuscript_drafts WHERE id=:id"),
                {"id": run["draft_id"]},
            )
            .mappings()
            .one()
        )
    draft = dict(draft_row)
    blocks = _blocks(draft.get("blocks"))
    modes = [str(item) for item in (_json(run.get("modes")) or [])]
    target_ids = {str(item) for item in (_json(run.get("block_ids")) or [])}
    result: dict[str, object] = {
        "artifacts": 0,
        "reviews": {},
        "source_revision": run["source_revision"],
    }
    try:
        if SEMANTIC_MODES.intersection(modes):
            connection = _connection(actor, settings)
            existing = _existing_hashes(actor, draft["id"])
            eligible = [
                item
                for item in blocks
                if (not target_ids or str(item.get("id") or "") in target_ids)
                and str(item.get("type") or "")
                in {
                    "title",
                    "heading",
                    "paragraph",
                    "list_item",
                    "caption",
                    "equation",
                    "table_row",
                    "image",
                }
                and (str(item.get("id") or ""), _block_hash(item)) not in existing
            ]
            batches = _batches(eligible)
            if batches:
                with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_CALLS, len(batches))) as pool:
                    futures = [pool.submit(_semantic_batch, connection, batch) for batch in batches]
                    for future in as_completed(futures):
                        for artifact in future.result():
                            _store_artifact(
                                actor,
                                draft,
                                block_id=str(artifact["block_id"]),
                                artifact_kind="block_semantics",
                                source_sha256=str(artifact["source_sha256"]),
                                content=dict(artifact["content"]),
                                model=connection.model,
                            )
                            result["artifacts"] = int(result["artifacts"]) + 1
            if "distill" in modes and _document_digest(actor, draft, blocks, connection):
                result["artifacts"] = int(result["artifacts"]) + 1
        review_modes = [
            item.removeprefix("review:")
            for item in modes
            if item.startswith("review:")
        ]
        if review_modes:
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_CALLS, len(review_modes))) as pool:
                futures = {
                    pool.submit(
                        _review_agent, actor, draft, blocks, agent_type, parsed_id, settings
                    ): agent_type
                    for agent_type in review_modes
                }
                for future in as_completed(futures):
                    result["reviews"][futures[future]] = future.result()
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text(
                    """
                    UPDATE research.manuscript_ai_runs
                    SET status='ready', result=CAST(:result AS jsonb), finished_at=now(), error=NULL
                    WHERE id=:id
                    """
                ),
                {"id": parsed_id, "result": json.dumps(result, ensure_ascii=False)},
            )
        return {"status": "ready", **result}
    except Exception as exc:
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text(
                    "UPDATE research.manuscript_ai_runs SET status='failed', error=:error, "
                    "finished_at=now() WHERE id=:id"
                ),
                {"id": parsed_id, "error": str(exc)[:2000]},
            )
        return {"status": "failed", "error": str(exc)[:2000]}


def agent_chat(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    agent_type: str,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    _require_write(actor)
    normalized_agent = str(agent_type).strip().lower()
    if normalized_agent not in AGENT_TYPES:
        raise HTTPException(status_code=404, detail="Unknown manuscript reviewer")
    message = str(payload.get("message") or "").strip()
    if not message or len(message) > 30_000:
        raise HTTPException(status_code=422, detail="message must contain 1–30000 characters")
    _project, _file, draft = _draft_target(actor, project_ref, file_ref)
    blocks = _blocks(draft.get("blocks"))
    selection = (
        _validated_selection(draft, payload.get("selection"))
        if payload.get("selection") is not None
        else None
    )
    citations = [selection] if selection else []
    thread_id = _thread(actor, draft, normalized_agent)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO research.manuscript_agent_messages(
                  id, tenant_id, project_id, file_id, draft_id, thread_id,
                  role, body, citations, context_revision, created_by
                ) VALUES (
                  :id, :tenant_id, :project_id, :file_id, :draft_id, :thread_id,
                  'user', :body, CAST(:citations AS jsonb), :revision, :created_by
                )
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "project_id": draft["project_id"],
                "file_id": draft["file_id"],
                "draft_id": draft["id"],
                "thread_id": thread_id,
                "body": message,
                "citations": json.dumps(citations, ensure_ascii=False),
                "revision": int(draft["revision"]),
                "created_by": actor.user_id,
            },
        )
        history = session.execute(
            text(
                "SELECT role,body FROM research.manuscript_agent_messages "
                "WHERE thread_id=:thread_id ORDER BY created_at DESC LIMIT 12"
            ),
            {"thread_id": thread_id},
        ).all()
    context = _review_context(
        actor,
        draft,
        blocks,
        include_findings=normalized_agent == "chief",
    )
    history_text = "\n".join(
        f"{str(role).upper()}: {body}" for role, body in reversed(history)
    )
    selection_text = ""
    if selection:
        selection_text = (
            "\n\n【用户当前选区 · 必须优先回答】\n"
            f"区块：{selection['block_id']}\n"
            f"原文：{selection['quote']}\n"
            f"前文：{selection['prefix']}\n"
            f"后文：{selection['suffix']}"
        )
    connection = _connection(
        actor,
        settings,
        thinking=normalized_agent in {"professional", "chief"},
    )
    answer = chat_completion(
        connection,
        system_prompt=(
            f"你是{AGENT_LABELS[normalized_agent]}。{AGENT_INSTRUCTIONS[normalized_agent]}"
            "回答必须基于提供的论文区块和已有评审；引用证据时写出区块 ID。"
            "如提供用户当前选区，必须先解释或评审该选区，再结合章节与全文上下文。"
            "你只能提出建议，不能声称已经修改正文。"
        ),
        user_prompt=(
            f"{context}{selection_text}\n\n【本线程最近对话】\n{history_text}"
            f"\n\n【用户问题】\n{message}"
        ),
        thinking=normalized_agent in {"professional", "chief"},
        max_tokens=3_000,
    )
    with tenant_session(actor.tenant_id) as session:
        message_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO research.manuscript_agent_messages(
                  id, tenant_id, project_id, file_id, draft_id, thread_id,
                  role, body, citations, context_revision, model, created_by
                ) VALUES (
                  :id, :tenant_id, :project_id, :file_id, :draft_id, :thread_id,
                  'assistant', :body, CAST(:citations AS jsonb),
                  :revision, :model, :created_by
                )
                """
            ),
            {
                "id": message_id,
                "tenant_id": actor.tenant_id,
                "project_id": draft["project_id"],
                "file_id": draft["file_id"],
                "draft_id": draft["id"],
                "thread_id": thread_id,
                "body": answer[:30_000],
                "citations": json.dumps(citations, ensure_ascii=False),
                "revision": int(draft["revision"]),
                "model": connection.model,
                "created_by": actor.user_id,
            },
        )
    return {
        "ok": True,
        "thread_id": str(thread_id),
        "message": {
            "id": str(message_id),
            "role": "assistant",
            "body": answer[:30_000],
            "citations": citations,
            "context_revision": int(draft["revision"]),
            "model": connection.model,
            "created_at": datetime.now(UTC).isoformat(),
        },
    }


def resolve_finding(
    actor: ActorContext,
    finding_id: object,
    *,
    accept: bool,
) -> dict[str, object]:
    _require_write(actor)
    parsed_id = UUID(str(finding_id))
    with tenant_session(actor.tenant_id) as session:
        finding_row = (
            session.execute(
                text("SELECT * FROM research.manuscript_findings WHERE id=:id FOR UPDATE"),
                {"id": parsed_id},
            )
            .mappings()
            .one_or_none()
        )
        if finding_row is None:
            raise HTTPException(status_code=404, detail="Manuscript finding not found")
        finding = dict(finding_row)
        if finding["status"] != "open":
            return {"ok": True, "finding_id": str(parsed_id), "status": finding["status"]}
        draft_row = (
            session.execute(
                text("SELECT * FROM research.manuscript_drafts WHERE id=:id FOR UPDATE"),
                {"id": finding["draft_id"]},
            )
            .mappings()
            .one()
        )
        draft = dict(draft_row)
        blocks = _blocks(draft.get("blocks"))
        block = next(
            (item for item in blocks if str(item.get("id") or "") == str(finding["block_id"])),
            None,
        )
        if block is None or _block_hash(block) != str(finding["source_sha256"]):
            session.execute(
                text(
                    "UPDATE research.manuscript_findings SET status='stale', "
                    "resolved_by=:user_id,resolved_at=now() WHERE id=:id"
                ),
                {"id": parsed_id, "user_id": actor.user_id},
            )
            raise HTTPException(
                status_code=409,
                detail="Finding is stale for the current paragraph",
            )
        if accept:
            suggestion = str(finding.get("suggestion") or "").strip()
            if not suggestion:
                raise HTTPException(status_code=422, detail="Finding has no applicable replacement")
            block["text"] = suggestion
            if block.get("type") == "table_row" and isinstance(block.get("cells"), list):
                block["cells"] = [part.strip() for part in suggestion.split("|")]
            session.execute(
                text(
                    """
                    UPDATE research.manuscript_drafts
                    SET blocks=CAST(:blocks AS jsonb), revision=revision+1,
                        state='active', updated_by=:user_id, updated_at=now()
                    WHERE id=:id
                    """
                ),
                {
                    "blocks": json.dumps(blocks, ensure_ascii=False),
                    "user_id": actor.user_id,
                    "id": draft["id"],
                },
            )
        state = "accepted" if accept else "rejected"
        session.execute(
            text(
                "UPDATE research.manuscript_findings SET status=:status, "
                "resolved_by=:user_id,resolved_at=now() WHERE id=:id"
            ),
            {"id": parsed_id, "status": state, "user_id": actor.user_id},
        )
    return {
        "ok": True,
        "finding_id": str(parsed_id),
        "status": state,
        "draft_revision": int(draft["revision"]) + (1 if accept else 0),
        "block": block if accept else None,
    }
