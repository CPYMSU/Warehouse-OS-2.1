"""Browser-local manuscript refinement with recoverable platform drafts."""

from __future__ import annotations

import io
import json
import re
import zipfile
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote
from uuid import UUID, uuid4
from xml.etree import ElementTree

from fastapi import HTTPException
from sqlalchemy import text

from app.api.deps import ActorContext
from app.core.config import Settings
from app.db.session import tenant_session
from app.services.object_storage import object_store_for_provider, object_store_read_candidates
from app.services.research_review import (
    W_NS,
    _blocks,
    _docx_relationships,
    _tag,
    _target_rows,
    ensure_document_index,
    queue_document_index,
)
from app.services.research_vault import add_file_version

MAX_BLOCKS = 5_000
MAX_CHARACTERS = 2_000_000
MAX_BLOCK_CHARACTERS = 120_000
MAX_TABLE_CELLS = 100
BLOCK_TYPES = frozenset(
    {
        "title",
        "heading",
        "paragraph",
        "list_item",
        "table_row",
        "equation",
        "caption",
        "image",
    }
)
BLOCK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,179}$")


def _require_write(actor: ActorContext) -> None:
    if "research.write" not in actor.permissions:
        raise HTTPException(status_code=403, detail="Research write permission denied")


def _source_path(settings: Settings, version: dict[str, object]) -> Path:
    for store in object_store_read_candidates(settings, str(version["storage_provider"])):
        path = store.path_for(str(version["object_key"]))
        if path.is_file():
            return path
    raise HTTPException(status_code=404, detail="Research object is unavailable")


def _initial_blocks(
    actor: ActorContext,
    version: dict[str, object],
    settings: Settings,
) -> list[dict[str, object]]:
    version_id = UUID(str(version["id"]))
    ensure_document_index(actor, version_id, settings)
    result: list[dict[str, object]] = []
    for row in _blocks(actor, version_id):
        locator = dict(row.get("locator") or {})
        block_type = str(row.get("block_type") or "paragraph")
        item: dict[str, object] = {
            "id": str(row["stable_key"]),
            "type": block_type,
            "text": str(row.get("content") or ""),
            "level": int(row["heading_level"]) if row.get("heading_level") else None,
            "source": locator,
        }
        if block_type == "table_row":
            cells = locator.get("cells")
            item["cells"] = (
                [str(value) for value in cells]
                if isinstance(cells, list)
                else [part.strip() for part in item["text"].split("|")]
            )
        result.append(item)
    return result


def _normalized_blocks(
    value: object,
    *,
    existing: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_BLOCKS:
        raise HTTPException(status_code=422, detail=f"Manuscript requires 1–{MAX_BLOCKS} blocks")
    source_by_id = {
        str(item.get("id")): dict(item.get("source") or {})
        for item in (existing or [])
        if isinstance(item, dict)
    }
    existing_type_by_id = {
        str(item.get("id")): str(item.get("type") or "")
        for item in (existing or [])
        if isinstance(item, dict)
    }
    normalized: list[dict[str, object]] = []
    identifiers: set[str] = set()
    total = 0
    for raw in value:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=422, detail="Manuscript block must be an object")
        identifier = str(raw.get("id") or "").strip()
        if not BLOCK_ID_RE.fullmatch(identifier) or identifier in identifiers:
            raise HTTPException(status_code=422, detail="Invalid or duplicate manuscript block id")
        identifiers.add(identifier)
        block_type = str(raw.get("type") or "paragraph").strip().lower()
        if block_type not in BLOCK_TYPES:
            raise HTTPException(status_code=422, detail="Unsupported manuscript block type")
        previous_type = existing_type_by_id.get(identifier)
        if previous_type == "image" and block_type != "image":
            raise HTTPException(status_code=422, detail="Imported figure blocks cannot change type")
        if block_type == "image" and previous_type != "image":
            raise HTTPException(
                status_code=422,
                detail="Upload new figures through the project library",
            )
        content = str(raw.get("text") or "").replace("\x00", "")
        if len(content) > MAX_BLOCK_CHARACTERS:
            raise HTTPException(status_code=422, detail="Manuscript block is too large")
        level_value = raw.get("level")
        try:
            level = int(level_value) if level_value not in {None, ""} else None
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Heading level is invalid") from exc
        if level is not None and not 1 <= level <= 9:
            raise HTTPException(status_code=422, detail="Heading level must be between 1 and 9")
        item: dict[str, object] = {
            "id": identifier,
            "type": block_type,
            "text": content,
            "level": level,
            "source": source_by_id.get(identifier, {}),
        }
        if block_type == "table_row":
            raw_cells = raw.get("cells")
            if not isinstance(raw_cells, list) or not 1 <= len(raw_cells) <= MAX_TABLE_CELLS:
                raise HTTPException(status_code=422, detail="Table rows require 1–100 cells")
            cells = [str(cell or "").replace("\x00", "") for cell in raw_cells]
            if any(len(cell) > MAX_BLOCK_CHARACTERS for cell in cells):
                raise HTTPException(status_code=422, detail="Table cell is too large")
            item["cells"] = cells
            item["text"] = " | ".join(cells)
        total += len(str(item["text"]))
        if total > MAX_CHARACTERS:
            raise HTTPException(status_code=422, detail="Manuscript draft exceeds character limit")
        normalized.append(item)
    return normalized


def _public_blocks(
    blocks: list[dict[str, object]],
    project_id: object,
    file_id: object,
    version_number: int,
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for raw in blocks:
        item = {key: value for key, value in raw.items() if key != "source"}
        source = dict(raw.get("source") or {})
        if raw.get("type") == "table_row" and source.get("table_index") is not None:
            item["table_key"] = int(source["table_index"])
            item["cell_spans"] = source.get("cell_spans") or []
        if source.get("contains_math"):
            item["contains_math"] = True
            item["latex"] = str(source.get("latex") or "")
        if raw.get("type") == "image" and source.get("relationship_id"):
            item["media_url"] = (
                f"/api/research/projects/{quote(str(project_id), safe='')}/files/"
                f"{quote(str(file_id), safe='')}/refinement/media/"
                f"{quote(str(source['relationship_id']), safe='')}?version={version_number}"
            )
            item["content_type"] = source.get("content_type")
        result.append(item)
    return result


def _draft_payload(
    row: dict[str, object],
    *,
    project: dict[str, object],
    file_row: dict[str, object],
    version: dict[str, object],
    source_changed: bool,
) -> dict[str, object]:
    blocks = row.get("blocks")
    if isinstance(blocks, str):
        blocks = json.loads(blocks)
    normalized = list(blocks) if isinstance(blocks, list) else []
    return {
        "source": "research_browser_local_refinement",
        "project": {"id": str(project["id"]), "title": project["title"]},
        "file": {
            "id": str(file_row["id"]),
            "logical_path": file_row["logical_path"],
            "display_name": file_row["display_name"],
        },
        "base_version": {
            "id": str(row["base_file_version_id"]),
            "version": int(version["version"]),
            "git_sha": version.get("git_sha"),
            "content_sha256": version["content_sha256"],
        },
        "draft": {
            "id": str(row["id"]),
            "revision": int(row["revision"]),
            "state": row["state"],
            "updated_at": str(row["updated_at"]),
            "submitted_at": str(row["submitted_at"]) if row.get("submitted_at") else None,
            "blocks": _public_blocks(
                normalized, project["id"], file_row["id"], int(version["version"])
            ),
        },
        "source_changed": source_changed,
        "capabilities": {
            "browser_compute": True,
            "autosave": True,
            "offline_copy": True,
            "text_blocks": True,
            "editable_tables": True,
            "source_figures": True,
            "formula_latex": True,
            "formula_source_fallback": True,
            "structured_table_spans": True,
            "paragraph_translation_zh_cn": True,
            "visible_distillation": True,
            "parallel_reviewers": True,
            "chief_context_bus": True,
            "formal_docx_version": Path(str(version["original_filename"])).suffix.lower()
            == ".docx",
            "office_runtime_required": False,
        },
    }


def refinement_workspace(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    settings: Settings,
) -> dict[str, object]:
    _require_write(actor)
    project, file_row, latest_version = _target_rows(actor, project_ref, file_ref, None)
    if Path(str(latest_version["original_filename"])).suffix.lower() != ".docx":
        raise HTTPException(status_code=422, detail="Manuscript refinement currently requires DOCX")
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text("SELECT * FROM research.manuscript_drafts WHERE file_id = :file_id"),
                {"file_id": file_row["id"]},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        blocks = _initial_blocks(actor, latest_version, settings)
        with tenant_session(actor.tenant_id) as session:
            row = (
                session.execute(
                    text(
                        """
                        INSERT INTO research.manuscript_drafts(
                          id, tenant_id, project_id, file_id, base_file_version_id,
                          blocks, created_by, updated_by
                        ) VALUES (
                          :id, :tenant_id, :project_id, :file_id, :version_id,
                          CAST(:blocks AS jsonb), :user_id, :user_id
                        )
                        ON CONFLICT (tenant_id, file_id) DO UPDATE SET file_id=EXCLUDED.file_id
                        RETURNING *
                        """
                    ),
                    {
                        "id": uuid4(),
                        "tenant_id": actor.tenant_id,
                        "project_id": project["id"],
                        "file_id": file_row["id"],
                        "version_id": latest_version["id"],
                        "blocks": json.dumps(blocks, ensure_ascii=False),
                        "user_id": actor.user_id,
                    },
                )
                .mappings()
                .one()
            )
    row = dict(row)
    source_changed = str(row["base_file_version_id"]) != str(latest_version["id"])
    base_version = latest_version
    if source_changed:
        _, _, base_version = _target_rows(
            actor, project["id"], file_row["id"], _draft_base_version(actor, row)
        )
    return _draft_payload(
        row,
        project=project,
        file_row=file_row,
        version=base_version,
        source_changed=source_changed,
    )


def _draft_base_version(actor: ActorContext, row: dict[str, object]) -> int:
    with tenant_session(actor.tenant_id) as session:
        value = session.execute(
            text("SELECT version FROM research.file_versions WHERE id = :id"),
            {"id": row["base_file_version_id"]},
        ).scalar_one_or_none()
    if value is None:
        raise HTTPException(status_code=409, detail="Manuscript base version is unavailable")
    return int(value)


def save_refinement_draft(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_write(actor)
    project, file_row, _latest = _target_rows(actor, project_ref, file_ref, None)
    try:
        expected_revision = int(payload.get("expected_revision", -1))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Draft revision is invalid") from exc
    with tenant_session(actor.tenant_id) as session:
        current = (
            session.execute(
                text(
                    "SELECT * FROM research.manuscript_drafts "
                    "WHERE file_id = :file_id FOR UPDATE"
                ),
                {"file_id": file_row["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if current is None:
            raise HTTPException(status_code=404, detail="Start manuscript refinement before saving")
        current = dict(current)
        if int(current["revision"]) != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Manuscript draft changed on another device",
                    "current_revision": int(current["revision"]),
                },
            )
        previous = current["blocks"]
        if isinstance(previous, str):
            previous = json.loads(previous)
        blocks = _normalized_blocks(payload.get("blocks"), existing=list(previous or []))
        updated = (
            session.execute(
                text(
                    """
                    UPDATE research.manuscript_drafts
                    SET blocks=CAST(:blocks AS jsonb), revision=revision + 1,
                        state='active', updated_by=:user_id, updated_at=now()
                    WHERE id=:id
                    RETURNING *
                    """
                ),
                {
                    "blocks": json.dumps(blocks, ensure_ascii=False),
                    "user_id": actor.user_id,
                    "id": current["id"],
                },
            )
            .mappings()
            .one()
        )
    base_number = _draft_base_version(actor, dict(updated))
    _, _, version = _target_rows(actor, project["id"], file_row["id"], base_number)
    return _draft_payload(
        dict(updated),
        project=project,
        file_row=file_row,
        version=version,
        source_changed=str(version["id"]) != str(_latest["id"]),
    )


def _append_text(paragraph: ElementTree.Element, value: str) -> None:
    parts = value.split("\n")
    run = ElementTree.SubElement(paragraph, _tag(W_NS, "r"))
    for index, part in enumerate(parts):
        if index:
            ElementTree.SubElement(run, _tag(W_NS, "br"))
        node = ElementTree.SubElement(run, _tag(W_NS, "t"))
        if part.startswith(" ") or part.endswith(" "):
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        node.text = part


def _paragraph(block: dict[str, object]) -> ElementTree.Element:
    paragraph = ElementTree.Element(_tag(W_NS, "p"))
    block_type = str(block.get("type") or "paragraph")
    style = ""
    if block_type == "title":
        style = "Title"
    elif block_type == "heading":
        style = f"Heading{max(1, min(int(block.get('level') or 1), 9))}"
    elif block_type == "caption":
        style = "Caption"
    elif block_type == "list_item":
        style = "ListParagraph"
    if style:
        properties = ElementTree.SubElement(paragraph, _tag(W_NS, "pPr"))
        style_node = ElementTree.SubElement(properties, _tag(W_NS, "pStyle"))
        style_node.set(_tag(W_NS, "val"), style)
    _append_text(paragraph, str(block.get("text") or ""))
    return paragraph


def _table(rows: list[dict[str, object]]) -> ElementTree.Element:
    table = ElementTree.Element(_tag(W_NS, "tbl"))
    for row in rows:
        row_node = ElementTree.SubElement(table, _tag(W_NS, "tr"))
        for cell in row.get("cells") or [row.get("text") or ""]:
            cell_node = ElementTree.SubElement(row_node, _tag(W_NS, "tc"))
            paragraph = ElementTree.SubElement(cell_node, _tag(W_NS, "p"))
            _append_text(paragraph, str(cell or ""))
    return table


def _assemble_docx(path: Path, blocks: list[dict[str, object]]) -> io.BytesIO:
    with zipfile.ZipFile(path) as source:
        entries = {name: source.read(name) for name in source.namelist()}
    try:
        root = ElementTree.fromstring(entries["word/document.xml"])
    except (KeyError, ElementTree.ParseError) as exc:
        raise HTTPException(
            status_code=422,
            detail="DOCX document structure is unavailable",
        ) from exc
    body = root.find(f".//{_tag(W_NS, 'body')}")
    if body is None:
        raise HTTPException(status_code=422, detail="DOCX document body is unavailable")
    original_children = list(body)
    section = next(
        (deepcopy(item) for item in original_children if item.tag == _tag(W_NS, "sectPr")),
        None,
    )
    body.clear()
    index = 0
    while index < len(blocks):
        block = blocks[index]
        if block.get("type") == "table_row":
            table_index = (block.get("source") or {}).get("table_index")
            rows: list[dict[str, object]] = []
            while index < len(blocks):
                candidate = blocks[index]
                if candidate.get("type") != "table_row":
                    break
                candidate_index = (candidate.get("source") or {}).get("table_index")
                if rows and candidate_index != table_index:
                    break
                rows.append(candidate)
                index += 1
            body.append(_table(rows))
            continue
        source = dict(block.get("source") or {})
        body_index = source.get("body_index")
        if (
            source.get("contains_math")
            and str(block.get("text") or "") == str(source.get("source_text") or "")
            and isinstance(body_index, int)
            and 0 <= body_index < len(original_children)
        ):
            body.append(deepcopy(original_children[body_index]))
            index += 1
            continue
        if block.get("type") == "image":
            if isinstance(body_index, int) and 0 <= body_index < len(original_children):
                image_paragraph = deepcopy(original_children[body_index])
                for text_node in image_paragraph.findall(f".//{_tag(W_NS, 't')}"):
                    text_node.text = ""
                body.append(image_paragraph)
        else:
            body.append(_paragraph(block))
        index += 1
    if section is not None:
        body.append(section)
    entries["word/document.xml"] = ElementTree.tostring(
        root, encoding="utf-8", xml_declaration=True
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as destination:
        for name, content in entries.items():
            destination.writestr(name, content)
    output.seek(0)
    return output


def publish_refinement(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    _require_write(actor)
    project, file_row, latest = _target_rows(actor, project_ref, file_ref, None)
    try:
        expected_revision = int(payload.get("expected_revision", -1))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Draft revision is invalid") from exc
    with tenant_session(actor.tenant_id) as session:
        draft = (
            session.execute(
                text("SELECT * FROM research.manuscript_drafts WHERE file_id=:file_id FOR UPDATE"),
                {"file_id": file_row["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if draft is None:
            raise HTTPException(status_code=404, detail="Manuscript draft not found")
        draft = dict(draft)
        if int(draft["revision"]) != expected_revision:
            raise HTTPException(
                status_code=409,
                detail="Save the latest manuscript draft before submitting",
            )
        if str(draft["base_file_version_id"]) != str(latest["id"]):
            raise HTTPException(
                status_code=409,
                detail="Source document has a newer formal version",
            )
    blocks = draft["blocks"]
    if isinstance(blocks, str):
        blocks = json.loads(blocks)
    normalized = _normalized_blocks(blocks, existing=list(blocks or []))
    document = _assemble_docx(_source_path(settings, latest), normalized)
    store = object_store_for_provider(settings, str(latest["storage_provider"]))
    stored = store.put_stream(
        tenant_id=actor.tenant_id,
        stream=document,
        max_bytes=settings.research_max_upload_bytes,
    )
    message = str(payload.get("commit_message") or "Submit browser manuscript refinement").strip()
    result = add_file_version(
        actor,
        project["id"],
        stored=stored,
        store=store,
        original_filename=str(latest["original_filename"]),
        content_type=str(latest["content_type"]),
        logical_path=str(file_row["logical_path"]),
        commit_message=message[:500],
        settings=settings,
    )
    new_version = result["version"]
    queue_document_index(actor, new_version["id"])
    refreshed_blocks = _initial_blocks(actor, {"id": new_version["id"]}, settings)
    with tenant_session(actor.tenant_id) as session:
        updated = (
            session.execute(
                text(
                    """
                    UPDATE research.manuscript_drafts
                    SET base_file_version_id=:version_id, revision=revision + 1,
                        blocks=CAST(:blocks AS jsonb), state='submitted',
                        submitted_at=now(), updated_by=:user_id, updated_at=now()
                    WHERE id=:id AND revision=:expected_revision
                    RETURNING revision
                    """
                ),
                {
                    "version_id": new_version["id"],
                    "blocks": json.dumps(refreshed_blocks, ensure_ascii=False),
                    "user_id": actor.user_id,
                    "id": draft["id"],
                    "expected_revision": expected_revision,
                },
            )
            .mappings()
            .one_or_none()
        )
    return {
        "ok": True,
        "source": "research_browser_local_refinement",
        "file": result["file"],
        "version": new_version,
        "git": result["git"],
        "draft_revision": int(updated["revision"]) if updated else expected_revision + 1,
    }


def refinement_media(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    relationship_id: str,
    version: int | None,
    settings: Settings,
) -> tuple[bytes, str]:
    if not actor.permissions.intersection({"research.read", "research.write"}):
        raise HTTPException(status_code=403, detail="Research read permission denied")
    project, file_row, version_row = _target_rows(actor, project_ref, file_ref, version)
    del project, file_row
    if Path(str(version_row["original_filename"])).suffix.lower() != ".docx":
        raise HTTPException(status_code=422, detail="Embedded media requires DOCX")
    path = _source_path(settings, version_row)
    with zipfile.ZipFile(path) as archive:
        relationship = _docx_relationships(archive).get(str(relationship_id))
        if relationship is None:
            raise HTTPException(status_code=404, detail="Embedded research figure not found")
        return archive.read(relationship["archive_path"]), relationship["content_type"]
