"""Version-pinned research-paper reading, annotation, and grounded AI services."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import posixpath
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from xml.etree import ElementTree

from fastapi import HTTPException, status
from sqlalchemy import text

from app.db.session import tenant_session
from app.services.integrations import (
    DEEPSEEK_RUNTIME_MODELS,
    ModelConnection,
    chat_completion,
    connected_deepseek,
)
from app.services.object_storage import LocalContentAddressedObjectStore
from app.services.research_vault import analyse_object

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings


PROCESSOR_VERSION = "word-review-v3"
MAX_AI_CONTEXT = 52_000
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


@dataclass(frozen=True)
class ParsedBlock:
    ordinal: int
    stable_key: str
    block_type: str
    heading_level: int | None
    heading_path: tuple[str, ...]
    content: str
    start_offset: int
    end_offset: int
    locator: dict[str, object]


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (UUID, datetime)):
        return str(value)
    return value


def _public_version(row: dict[str, object]) -> dict[str, object]:
    """Expose immutable version identity without leaking storage internals."""

    return {
        "id": str(row["id"]),
        "version": int(row["version"]),
        "filename": str(row["original_filename"]),
        "content_type": str(row["content_type"]),
        "content_sha256": str(row["content_sha256"]),
        "size_bytes": int(row["size_bytes"]),
        "git_sha": row.get("git_sha"),
        "commit_message": row.get("commit_message"),
        "created_by": str(row["created_by"]) if row.get("created_by") else None,
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
    }


def _require_read(actor: ActorContext) -> None:
    if "research.read" not in actor.permissions:
        raise HTTPException(status_code=403, detail="Research read permission denied")


def _require_annotate(actor: ActorContext) -> None:
    if actor.permissions.intersection({"research.write", "research.review"}):
        return
    raise HTTPException(status_code=403, detail="Research annotation permission denied")


def _audit(session: object, actor: ActorContext, event: str, payload: dict[str, object]) -> None:
    session.execute(
        text(
            """
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (:tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb))
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "actor_user_id": actor.user_id,
            "event_type": event,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _target_rows(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    version: int | None,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        project = (
            session.execute(
                text(
                    """
                    SELECT * FROM research.projects
                    WHERE id::text = :project_ref OR slug = :project_ref
                    LIMIT 1
                    """
                ),
                {"project_ref": str(project_ref)},
            )
            .mappings()
            .one_or_none()
        )
        if project is None:
            raise HTTPException(status_code=404, detail="Research project not found")
        file_row = (
            session.execute(
                text(
                    """
                    SELECT * FROM research.files
                    WHERE project_id = :project_id
                      AND (id::text = :file_ref OR logical_path = :file_ref)
                    LIMIT 1
                    """
                ),
                {"project_id": project["id"], "file_ref": str(file_ref)},
            )
            .mappings()
            .one_or_none()
        )
        if file_row is None:
            raise HTTPException(status_code=404, detail="Research file not found")
        condition = "AND version = :version" if version is not None else ""
        params: dict[str, object] = {
            "project_id": project["id"],
            "file_id": file_row["id"],
        }
        if version is not None:
            params["version"] = version
        version_row = (
            session.execute(
                text(
                    f"""
                    SELECT * FROM research.file_versions
                    WHERE project_id = :project_id AND file_id = :file_id {condition}
                    ORDER BY version DESC LIMIT 1
                    """
                ),
                params,
            )
            .mappings()
            .one_or_none()
        )
        if version_row is None:
            raise HTTPException(status_code=404, detail="Research file version not found")
    return dict(project), dict(file_row), dict(version_row)


def _version_target(actor: ActorContext, version_id: UUID) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT v.*, f.file_kind, f.logical_path
                    FROM research.file_versions v
                    JOIN research.files f ON f.id = v.file_id
                    WHERE v.id = :version_id
                    """
                ),
                {"version_id": version_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Research file version not found")
    return dict(row)


def _tag(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def _docx_styles(archive: zipfile.ZipFile) -> dict[str, str]:
    try:
        root = ElementTree.fromstring(archive.read("word/styles.xml"))
    except (KeyError, ElementTree.ParseError):
        return {}
    styles: dict[str, str] = {}
    for style in root.findall(f".//{_tag(W_NS, 'style')}"):
        style_id = style.attrib.get(_tag(W_NS, "styleId"), "")
        name = style.find(_tag(W_NS, "name"))
        if style_id:
            styles[style_id] = (
                name.attrib.get(_tag(W_NS, "val"), style_id) if name is not None else style_id
            )
    return styles


def _node_text(node: ElementTree.Element, *, include_image_labels: bool = True) -> str:
    parts: list[str] = []
    seen_images: set[str] = set()
    for item in node.iter():
        if item.tag in {_tag(W_NS, "t"), _tag(M_NS, "t")}:
            parts.append(item.text or "")
        elif item.tag == _tag(W_NS, "tab"):
            parts.append("\t")
        elif item.tag in {_tag(W_NS, "br"), _tag(W_NS, "cr")}:
            parts.append("\n")
        elif include_image_labels and item.tag == _tag(WP_NS, "docPr"):
            label = str(item.attrib.get("descr") or item.attrib.get("title") or "").strip()
            if label and label not in seen_images:
                seen_images.add(label)
                parts.append(f" [圖：{label}] ")
    return re.sub(r"[ \u00a0]+", " ", "".join(parts)).strip()


def _local_name(node: ElementTree.Element) -> str:
    return node.tag.rsplit("}", 1)[-1]


def _omml_to_latex(node: ElementTree.Element) -> str:
    """Preserve common Word equations as editable, browser-renderable LaTeX."""

    name = _local_name(node)
    children = list(node)
    if name == "t":
        return str(node.text or "")
    if name in {"oMath", "oMathPara", "r", "e", "num", "den", "sup", "sub", "deg"}:
        return "".join(_omml_to_latex(child) for child in children)
    if name == "f":
        numerator = node.find(f"./{_tag(M_NS, 'num')}")
        denominator = node.find(f"./{_tag(M_NS, 'den')}")
        return "\\frac{" + (_omml_to_latex(numerator) if numerator is not None else "") + "}{" + (
            _omml_to_latex(denominator) if denominator is not None else ""
        ) + "}"
    if name in {"sSup", "sSub", "sSubSup"}:
        expression = node.find(f"./{_tag(M_NS, 'e')}")
        subscript = node.find(f"./{_tag(M_NS, 'sub')}")
        superscript = node.find(f"./{_tag(M_NS, 'sup')}")
        value = _omml_to_latex(expression) if expression is not None else ""
        if subscript is not None:
            value += "_{" + _omml_to_latex(subscript) + "}"
        if superscript is not None:
            value += "^{" + _omml_to_latex(superscript) + "}"
        return value
    if name == "rad":
        degree = node.find(f"./{_tag(M_NS, 'deg')}")
        expression = node.find(f"./{_tag(M_NS, 'e')}")
        degree_value = _omml_to_latex(degree) if degree is not None else ""
        expression_value = _omml_to_latex(expression) if expression is not None else ""
        return (
            "\\sqrt[" + degree_value + "]{" + expression_value + "}"
            if degree_value
            else "\\sqrt{" + expression_value + "}"
        )
    if name == "d":
        expression = node.find(f"./{_tag(M_NS, 'e')}")
        value = _omml_to_latex(expression) if expression is not None else ""
        return "\\left(" + value + "\\right)"
    if name == "nary":
        operator = "\\sum"
        character = node.find(f".//{_tag(M_NS, 'chr')}")
        raw_character = character.attrib.get(_tag(M_NS, "val"), "") if character is not None else ""
        operator = {"∫": "\\int", "∏": "\\prod", "∑": "\\sum"}.get(
            raw_character, operator
        )
        subscript = node.find(f"./{_tag(M_NS, 'sub')}")
        superscript = node.find(f"./{_tag(M_NS, 'sup')}")
        expression = node.find(f"./{_tag(M_NS, 'e')}")
        if subscript is not None:
            operator += "_{" + _omml_to_latex(subscript) + "}"
        if superscript is not None:
            operator += "^{" + _omml_to_latex(superscript) + "}"
        return operator + " " + (_omml_to_latex(expression) if expression is not None else "")
    if name == "m":
        rows: list[str] = []
        for row in node.findall(f"./{_tag(M_NS, 'mr')}"):
            cells = row.findall(f"./{_tag(M_NS, 'e')}")
            rows.append(" & ".join(_omml_to_latex(cell) for cell in cells))
        return "\\begin{matrix}" + " \\\\ ".join(rows) + "\\end{matrix}"
    if name == "func":
        function_name = node.find(f"./{_tag(M_NS, 'fName')}")
        expression = node.find(f"./{_tag(M_NS, 'e')}")
        return (
            (_omml_to_latex(function_name) if function_name is not None else "")
            + " "
            + (_omml_to_latex(expression) if expression is not None else "")
        )
    return "".join(_omml_to_latex(child) for child in children)


def _docx_relationships(archive: zipfile.ZipFile) -> dict[str, dict[str, str]]:
    try:
        root = ElementTree.fromstring(archive.read("word/_rels/document.xml.rels"))
    except (KeyError, ElementTree.ParseError):
        return {}
    relationships: dict[str, dict[str, str]] = {}
    for item in root.findall(_tag(REL_NS, "Relationship")):
        relationship_id = str(item.attrib.get("Id") or "").strip()
        target = str(item.attrib.get("Target") or "").strip()
        if not relationship_id or not target or item.attrib.get("TargetMode") == "External":
            continue
        normalized_target = target.lstrip("/")
        archive_path = posixpath.normpath(
            normalized_target
            if normalized_target.startswith("word/")
            else posixpath.join("word", normalized_target)
        )
        if archive_path.startswith("word/media/") and archive_path in archive.namelist():
            relationships[relationship_id] = {
                "relationship_id": relationship_id,
                "archive_path": archive_path,
                "content_type": mimetypes.guess_type(archive_path)[0]
                or "application/octet-stream",
            }
    return relationships


def _paragraph_images(
    paragraph: ElementTree.Element,
    relationships: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    labels = [
        str(item.attrib.get("descr") or item.attrib.get("title") or item.attrib.get("name") or "")
        .strip()
        for item in paragraph.findall(f".//{_tag(WP_NS, 'docPr')}")
    ]
    images: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(paragraph.findall(f".//{_tag(A_NS, 'blip')}")):
        relationship_id = str(item.attrib.get(_tag(R_NS, "embed")) or "").strip()
        relationship = relationships.get(relationship_id)
        if not relationship or relationship_id in seen:
            continue
        seen.add(relationship_id)
        images.append(
            {
                **relationship,
                "alt_text": (
                    labels[index] if index < len(labels) and labels[index] else "Research figure"
                ),
            }
        )
    return images


def _paragraph_style(paragraph: ElementTree.Element, styles: dict[str, str]) -> str:
    style = paragraph.find(f"./{_tag(W_NS, 'pPr')}/{_tag(W_NS, 'pStyle')}")
    if style is None:
        return ""
    style_id = style.attrib.get(_tag(W_NS, "val"), "")
    return styles.get(style_id, style_id)


def _heading_level(style_name: str) -> int | None:
    normalized = re.sub(r"[ _-]+", "", style_name).lower()
    if normalized in {"title", "documenttitle", "論文標題", "标题"}:
        return 1
    match = re.search(r"(?:heading|標題|标题)([1-9])", normalized)
    return int(match.group(1)) if match else None


def _raw_docx_blocks(path: Path) -> list[dict[str, object]]:
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
        styles = _docx_styles(archive)
        relationships = _docx_relationships(archive)
    body = root.find(f".//{_tag(W_NS, 'body')}")
    if body is None:
        return []
    raw: list[dict[str, object]] = []
    paragraph_index = 0
    table_index = 0
    for body_index, child in enumerate(list(body)):
        if child.tag == _tag(W_NS, "p"):
            value = _node_text(child, include_image_labels=False)
            images = _paragraph_images(child, relationships)
            current_paragraph = paragraph_index
            paragraph_index += 1
            style_name = _paragraph_style(child, styles)
            level = _heading_level(style_name)
            has_numbering = child.find(
                f"./{_tag(W_NS, 'pPr')}/{_tag(W_NS, 'numPr')}"
            ) is not None
            math_nodes = child.findall(f".//{_tag(M_NS, 'oMath')}")
            has_math = bool(math_nodes)
            latex = " ".join(_omml_to_latex(item) for item in math_nodes).strip()
            if level == 1 and re.sub(r"[ _-]+", "", style_name).lower() in {
                "title",
                "documenttitle",
                "論文標題",
                "标题",
            }:
                block_type = "title"
            elif level:
                block_type = "heading"
            elif "caption" in style_name.lower() or "圖說" in style_name:
                block_type = "caption"
            elif has_math and not child.findall(f".//{_tag(W_NS, 't')}"):
                block_type = "equation"
            elif has_numbering:
                block_type = "list_item"
            else:
                block_type = "paragraph"
            if value:
                raw.append(
                    {
                        "block_type": block_type,
                        "heading_level": level,
                        "content": value,
                        "locator": {
                            "format": "docx-openxml",
                            "body_index": body_index,
                            "paragraph_index": current_paragraph,
                            "style": style_name or None,
                            "contains_math": has_math,
                            "latex": latex or None,
                            "source_text": value,
                        },
                    }
                )
            for image in images:
                raw.append(
                    {
                        "block_type": "image",
                        "heading_level": None,
                        "content": image["alt_text"],
                        "locator": {
                            "format": "docx-openxml",
                            "body_index": body_index,
                            "paragraph_index": current_paragraph,
                            **image,
                        },
                    }
                )
        elif child.tag == _tag(W_NS, "tbl"):
            current_table = table_index
            table_index += 1
            for row_index, row in enumerate(child.findall(f"./{_tag(W_NS, 'tr')}")):
                cells = [
                    _node_text(cell)
                    for cell in row.findall(f"./{_tag(W_NS, 'tc')}")
                ]
                cell_spans: list[dict[str, object]] = []
                for cell in row.findall(f"./{_tag(W_NS, 'tc')}"):
                    grid_span = cell.find(
                        f"./{_tag(W_NS, 'tcPr')}/{_tag(W_NS, 'gridSpan')}"
                    )
                    vertical_merge = cell.find(
                        f"./{_tag(W_NS, 'tcPr')}/{_tag(W_NS, 'vMerge')}"
                    )
                    cell_spans.append(
                        {
                            "colspan": int(grid_span.attrib.get(_tag(W_NS, "val"), "1"))
                            if grid_span is not None
                            else 1,
                            "vertical_merge": vertical_merge.attrib.get(
                                _tag(W_NS, "val"), "continue"
                            )
                            if vertical_merge is not None
                            else None,
                        }
                    )
                value = " | ".join(cells).strip(" |")
                if value:
                    raw.append(
                        {
                            "block_type": "table_row",
                            "heading_level": None,
                            "content": value,
                            "locator": {
                                "format": "docx-openxml",
                                "body_index": body_index,
                                "table_index": current_table,
                                "row_index": row_index,
                                "cell_count": len(cells),
                                "cells": cells,
                                "cell_spans": cell_spans,
                            },
                        }
                    )
    return raw


def _raw_text_blocks(path: Path, target: dict[str, object]) -> list[dict[str, object]]:
    analysis = analyse_object(
        path,
        str(target["original_filename"]),
        str(target["content_type"]),
        int(target["size_bytes"]),
    )
    extracted = analysis.extracted_text or ""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n|(?<=\n)", extracted) if part.strip()]
    block_type = "page" if analysis.file_kind == "pdf" else (
        "code" if analysis.file_kind in {"code", "notebook"} else "paragraph"
    )
    return [
        {
            "block_type": block_type,
            "heading_level": None,
            "content": part,
            "locator": {"format": analysis.file_kind, "source_index": index},
        }
        for index, part in enumerate(paragraphs)
    ]


def parse_document_blocks(path: Path, target: dict[str, object]) -> list[ParsedBlock]:
    extension = Path(str(target["original_filename"])).suffix.lower()
    raw = _raw_docx_blocks(path) if extension == ".docx" else _raw_text_blocks(path, target)
    blocks: list[ParsedBlock] = []
    document_title: list[str] = []
    headings: list[str] = []
    offset = 0
    duplicate_keys: dict[str, int] = {}
    for ordinal, item in enumerate(raw):
        content = str(item["content"])
        level = item.get("heading_level")
        if item["block_type"] == "title":
            document_title = [content]
        elif isinstance(level, int):
            headings = headings[: max(0, level - 1)]
            headings.append(content)
        digest = hashlib.sha256(f"{item['block_type']}\x00{content}".encode()).hexdigest()[:24]
        duplicate_index = duplicate_keys.get(digest, 0)
        duplicate_keys[digest] = duplicate_index + 1
        stable_key = f"{digest}-{duplicate_index}"
        end = offset + len(content)
        blocks.append(
            ParsedBlock(
                ordinal=ordinal,
                stable_key=stable_key,
                block_type=str(item["block_type"]),
                heading_level=level if isinstance(level, int) else None,
                heading_path=tuple(document_title + headings),
                content=content,
                start_offset=offset,
                end_offset=end,
                locator=dict(item["locator"]),
            )
        )
        offset = end + 2
    return blocks


def queue_document_index(actor: ActorContext, version_id: object) -> None:
    """Create the durable derived-index record without delaying an upload response."""

    try:
        parsed_id = UUID(str(version_id))
    except ValueError:
        return
    target = _version_target(actor, parsed_id)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO research.document_indexes(
                  id, tenant_id, project_id, file_id, file_version_id,
                  status, distillation_status, processor_version
                ) VALUES (
                  :id, :tenant_id, :project_id, :file_id, :file_version_id,
                  'queued', 'queued', :processor_version
                ) ON CONFLICT (tenant_id, file_version_id) DO NOTHING
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "project_id": target["project_id"],
                "file_id": target["file_id"],
                "file_version_id": parsed_id,
                "processor_version": PROCESSOR_VERSION,
            },
        )


def index_document_version(
    actor: ActorContext,
    version_id: object,
    settings: Settings,
) -> dict[str, object]:
    parsed_id = UUID(str(version_id))
    target = _version_target(actor, parsed_id)
    queue_document_index(actor, parsed_id)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE research.document_indexes
                SET status = 'indexing', error = NULL, processor_version = :processor_version
                WHERE file_version_id = :file_version_id
                """
            ),
            {"file_version_id": parsed_id, "processor_version": PROCESSOR_VERSION},
        )
    try:
        store = LocalContentAddressedObjectStore(settings.asset_storage_root)
        path = store.path_for(str(target["object_key"]))
        if not path.is_file():
            raise FileNotFoundError("Research object is unavailable")
        blocks = parse_document_blocks(path, target)
        canonical = "\n\n".join(item.content for item in blocks)
        outline = [
            {
                "ordinal": item.ordinal,
                "level": item.heading_level,
                "title": item.content,
            }
            for item in blocks
            if item.block_type in {"title", "heading"}
        ]
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text("DELETE FROM research.document_blocks WHERE file_version_id = :version_id"),
                {"version_id": parsed_id},
            )
            for item in blocks:
                session.execute(
                    text(
                        """
                        INSERT INTO research.document_blocks(
                          id, tenant_id, project_id, file_id, file_version_id,
                          ordinal, stable_key, block_type, heading_level, heading_path,
                          content, start_offset, end_offset, locator
                        ) VALUES (
                          :id, :tenant_id, :project_id, :file_id, :file_version_id,
                          :ordinal, :stable_key, :block_type, :heading_level, :heading_path,
                          :content, :start_offset, :end_offset, CAST(:locator AS jsonb)
                        )
                        """
                    ),
                    {
                        "id": uuid4(),
                        "tenant_id": actor.tenant_id,
                        "project_id": target["project_id"],
                        "file_id": target["file_id"],
                        "file_version_id": parsed_id,
                        "ordinal": item.ordinal,
                        "stable_key": item.stable_key,
                        "block_type": item.block_type,
                        "heading_level": item.heading_level,
                        "heading_path": list(item.heading_path),
                        "content": item.content,
                        "start_offset": item.start_offset,
                        "end_offset": item.end_offset,
                        "locator": json.dumps(item.locator, ensure_ascii=False),
                    },
                )
            session.execute(
                text(
                    """
                    UPDATE research.document_indexes
                    SET status = 'ready', canonical_sha256 = :canonical_sha256,
                        block_count = :block_count, character_count = :character_count,
                        outline = CAST(:outline AS jsonb), indexed_at = now(), error = NULL
                    WHERE file_version_id = :file_version_id
                    """
                ),
                {
                    "file_version_id": parsed_id,
                    "canonical_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                    "block_count": len(blocks),
                    "character_count": len(canonical),
                    "outline": json.dumps(outline, ensure_ascii=False),
                },
            )
        return {"status": "ready", "blocks": len(blocks), "characters": len(canonical)}
    except Exception as exc:
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text(
                    """
                    UPDATE research.document_indexes
                    SET status = 'failed', error = :error
                    WHERE file_version_id = :file_version_id
                    """
                ),
                {"file_version_id": parsed_id, "error": str(exc)[:2000]},
            )
        raise


def _index_row(actor: ActorContext, version_id: UUID) -> dict[str, object] | None:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text("SELECT * FROM research.document_indexes WHERE file_version_id = :id"),
                {"id": version_id},
            )
            .mappings()
            .one_or_none()
        )
    return dict(row) if row else None


def ensure_document_index(
    actor: ActorContext,
    version_id: UUID,
    settings: Settings,
) -> dict[str, object]:
    current = _index_row(actor, version_id)
    if (
        current
        and current.get("status") == "ready"
        and current.get("processor_version") == PROCESSOR_VERSION
    ):
        return current
    index_document_version(actor, version_id, settings)
    return _index_row(actor, version_id) or {}


def _blocks(actor: ActorContext, version_id: UUID) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, ordinal, stable_key, block_type, heading_level,
                           heading_path, content, start_offset, end_offset, locator,
                           distilled_context
                    FROM research.document_blocks
                    WHERE file_version_id = :version_id
                    ORDER BY ordinal
                    """
                ),
                {"version_id": version_id},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def _parse_model_json(value: str) -> dict[str, object]:
    candidate = value.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    payload = json.loads(candidate)
    if not isinstance(payload, dict):
        raise ValueError("AI response must be a JSON object")
    return payload


def distill_document_index(
    actor: ActorContext,
    version_id: object,
    settings: Settings,
) -> dict[str, object]:
    """Build a compact concept map in a durable post-response job."""

    parsed_id = UUID(str(version_id))
    ensure_document_index(actor, parsed_id, settings)
    blocks = _blocks(actor, parsed_id)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE research.document_indexes
                SET distillation_status = 'processing', error = NULL
                WHERE file_version_id = :version_id
                """
            ),
            {"version_id": parsed_id},
        )
    try:
        connection = connected_deepseek(actor, settings)
        balanced = ModelConnection(
            base_url=connection.base_url,
            model=DEEPSEEK_RUNTIME_MODELS["balanced"],
            api_key=connection.api_key,
        )
        excerpts: list[str] = []
        used = 0
        for block in blocks:
            line = f"[B{int(block['ordinal']):04d}] {block['content']}"
            if used + len(line) > MAX_AI_CONTEXT:
                break
            excerpts.append(line)
            used += len(line)
        response = chat_completion(
            balanced,
            system_prompt=(
                "你是科研文獻索引員。只根據提供的版本固定文件建立概念索引，不補造事實。"
                "輸出 JSON：summary 為文件摘要；concepts 為陣列，每項含 name、aliases、definition、"
                "block_ordinals；outline_notes 為陣列。所有 block_ordinals 必須引用輸入的 B 編號。"
            ),
            user_prompt="\n".join(excerpts),
            thinking=False,
            max_tokens=2_800,
            json_mode=True,
        )
        payload = _parse_model_json(response)
        valid_ordinals = {int(block["ordinal"]) for block in blocks}
        concepts: list[dict[str, object]] = []
        for raw in payload.get("concepts") or []:
            if not isinstance(raw, dict):
                continue
            ordinals = [
                int(value)
                for value in raw.get("block_ordinals") or []
                if str(value).isdigit() and int(value) in valid_ordinals
            ]
            name = str(raw.get("name") or "").strip()
            if name and ordinals:
                concepts.append(
                    {
                        "name": name[:300],
                        "aliases": [str(item)[:200] for item in raw.get("aliases") or []][:12],
                        "definition": str(raw.get("definition") or "")[:3000],
                        "block_ordinals": sorted(set(ordinals))[:30],
                    }
                )
        summary = str(payload.get("summary") or "").strip()[:12000]
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text(
                    """
                    UPDATE research.document_indexes
                    SET distillation_status = 'ready', summary = :summary,
                        concepts = CAST(:concepts AS jsonb), distilled_at = now(), error = NULL
                    WHERE file_version_id = :version_id
                    """
                ),
                {
                    "version_id": parsed_id,
                    "summary": summary,
                    "concepts": json.dumps(concepts, ensure_ascii=False),
                },
            )
            for concept in concepts:
                for ordinal in concept["block_ordinals"]:
                    session.execute(
                        text(
                            """
                            UPDATE research.document_blocks
                            SET distilled_context = jsonb_set(
                              distilled_context, '{concepts}',
                              COALESCE(distilled_context->'concepts', '[]'::jsonb)
                                || CAST(:concept AS jsonb),
                              true
                            )
                            WHERE file_version_id = :version_id AND ordinal = :ordinal
                            """
                        ),
                        {
                            "version_id": parsed_id,
                            "ordinal": ordinal,
                            "concept": json.dumps(
                                {"name": concept["name"], "definition": concept["definition"]},
                                ensure_ascii=False,
                            ),
                        },
                    )
        return {"status": "ready", "concepts": len(concepts), "model": balanced.model}
    except ValueError as exc:
        unavailable = (
            "configured" in str(exc).lower() or "validation" in str(exc).lower()
        )
        state = "unavailable" if unavailable else "failed"
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text(
                    """
                    UPDATE research.document_indexes
                    SET distillation_status = :state, error = :error
                    WHERE file_version_id = :version_id
                    """
                ),
                {"version_id": parsed_id, "state": state, "error": str(exc)[:2000]},
            )
        return {"status": state, "error": str(exc)}
    except Exception as exc:
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text(
                    """
                    UPDATE research.document_indexes
                    SET distillation_status = 'failed', error = :error
                    WHERE file_version_id = :version_id
                    """
                ),
                {"version_id": parsed_id, "error": str(exc)[:2000]},
            )
        return {"status": "failed", "error": str(exc)}


def _canonical(blocks: list[dict[str, object]]) -> str:
    return "\n\n".join(str(item["content"]) for item in blocks)


def _common_suffix(left: str, right: str) -> int:
    length = 0
    for a, b in zip(reversed(left), reversed(right), strict=False):
        if a != b:
            break
        length += 1
    return length


def _common_prefix(left: str, right: str) -> int:
    length = 0
    for a, b in zip(left, right, strict=False):
        if a != b:
            break
        length += 1
    return length


def _collapsed_with_map(value: str) -> tuple[str, list[int]]:
    normalized: list[str] = []
    offsets: list[int] = []
    in_space = False
    for index, character in enumerate(value):
        if character.isspace():
            if not in_space:
                normalized.append(" ")
                offsets.append(index)
            in_space = True
        else:
            normalized.append(character)
            offsets.append(index)
            in_space = False
    return "".join(normalized), offsets


def resolve_anchor(
    blocks: list[dict[str, object]], raw_anchor: object
) -> dict[str, object]:
    if not isinstance(raw_anchor, dict):
        raise HTTPException(status_code=422, detail="selection anchor is required")
    quote = str(raw_anchor.get("quote") or "").strip()
    if not quote or len(quote) > 12000:
        raise HTTPException(status_code=422, detail="selected text must contain 1–12000 characters")
    canonical = _canonical(blocks)
    prefix = str(raw_anchor.get("prefix") or "")[-240:]
    suffix = str(raw_anchor.get("suffix") or "")[:240]
    candidates: list[int] = []
    cursor = canonical.find(quote)
    while cursor >= 0:
        candidates.append(cursor)
        cursor = canonical.find(quote, cursor + 1)
    exact = bool(candidates)
    if candidates:
        start = max(
            candidates,
            key=lambda item: _common_suffix(canonical[max(0, item - len(prefix)) : item], prefix)
            + _common_prefix(
                canonical[item + len(quote) : item + len(quote) + len(suffix)], suffix
            ),
        )
        end = start + len(quote)
    else:
        collapsed, mapping = _collapsed_with_map(canonical)
        collapsed_quote, _ = _collapsed_with_map(quote)
        normalized_start = collapsed.find(collapsed_quote.strip())
        if normalized_start < 0 or not mapping:
            raise HTTPException(
                status_code=409,
                detail="Selected text cannot be anchored to this immutable file version",
            )
        normalized_end = normalized_start + len(collapsed_quote.strip()) - 1
        start = mapping[normalized_start]
        end = mapping[min(normalized_end, len(mapping) - 1)] + 1
        quote = canonical[start:end]
    touched = [
        item
        for item in blocks
        if int(item["end_offset"]) > start and int(item["start_offset"]) < end
    ]
    if not touched:
        raise HTTPException(status_code=409, detail="Selection does not overlap a document block")
    first, last = touched[0], touched[-1]
    return {
        "schema": "research-text-anchor/v1",
        "state": "exact" if exact else "normalized",
        "start": start,
        "end": end,
        "quote": quote,
        "prefix": canonical[max(0, start - 120) : start],
        "suffix": canonical[end : end + 120],
        "start_block_id": str(first["id"]),
        "start_block_ordinal": int(first["ordinal"]),
        "end_block_id": str(last["id"]),
        "end_block_ordinal": int(last["ordinal"]),
        "anchor_sha256": hashlib.sha256(f"{start}\x00{end}\x00{quote}".encode()).hexdigest(),
    }


def _annotation_rows(actor: ActorContext, version_id: UUID) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT a.*, u.display_name AS author_name,
                           COALESCE((
                             SELECT jsonb_agg(jsonb_build_object(
                               'id', m.id, 'message_kind', m.message_kind, 'body', m.body,
                               'citations', m.citations, 'created_at', m.created_at,
                               'author_name', mu.display_name
                             ) ORDER BY m.created_at)
                             FROM research.document_annotation_messages m
                             LEFT JOIN iam.users mu ON mu.id = m.created_by
                             WHERE m.annotation_id = a.id
                           ), '[]'::jsonb) AS messages
                    FROM research.document_annotations a
                    LEFT JOIN iam.users u ON u.id = a.created_by
                    WHERE a.file_version_id = :version_id
                    ORDER BY a.status, a.created_at
                    """
                ),
                {"version_id": version_id},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def document_workspace(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    version: int | None,
    settings: Settings,
) -> dict[str, object]:
    _require_read(actor)
    project, file_row, version_row = _target_rows(actor, project_ref, file_ref, version)
    index = ensure_document_index(actor, UUID(str(version_row["id"])), settings)
    blocks = _blocks(actor, UUID(str(version_row["id"])))
    with tenant_session(actor.tenant_id) as session:
        questions = (
            session.execute(
                text(
                    """
                    SELECT q.*, u.display_name AS asker_name
                    FROM research.document_questions q
                    LEFT JOIN iam.users u ON u.id = q.asked_by
                    WHERE q.file_version_id = :version_id
                    ORDER BY q.created_at DESC LIMIT 30
                    """
                ),
                {"version_id": version_row["id"]},
            )
            .mappings()
            .all()
        )
    return {
        "source": "research_versioned_review",
        "project": _json_safe(project),
        "file": _json_safe(file_row),
        "version": _public_version(version_row),
        "index": _json_safe(index),
        "blocks": _json_safe(blocks),
        "annotations": _json_safe(_annotation_rows(actor, UUID(str(version_row["id"])))),
        "questions": _json_safe([dict(row) for row in questions]),
        "capabilities": {
            "character_anchors": True,
            "paragraph_review": True,
            "grounded_ai": True,
            "version_pinned": True,
            "docx_fidelity": "openxml_html_mathml",
        },
    }


def create_annotation(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    _require_annotate(actor)
    version = int(payload["version"]) if payload.get("version") is not None else None
    project, file_row, version_row = _target_rows(actor, project_ref, file_ref, version)
    version_id = UUID(str(version_row["id"]))
    ensure_document_index(actor, version_id, settings)
    anchor = resolve_anchor(_blocks(actor, version_id), payload.get("anchor"))
    body = str(payload.get("body") or "").strip()
    if not body or len(body) > 20000:
        raise HTTPException(
            status_code=422, detail="annotation body must contain 1–20000 characters"
        )
    annotation_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.document_annotations(
                      id, tenant_id, project_id, file_id, file_version_id,
                      anchor, quote, body, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :file_id, :file_version_id,
                      CAST(:anchor AS jsonb), :quote, :body, :created_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": annotation_id,
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "file_id": file_row["id"],
                    "file_version_id": version_id,
                    "anchor": json.dumps(anchor, ensure_ascii=False),
                    "quote": anchor["quote"],
                    "body": body,
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.document.annotation.created",
            {"annotation_id": annotation_id, "file_version_id": version_id, "anchor": anchor},
        )
    return {"ok": True, "annotation": _json_safe(dict(row))}


def add_annotation_message(
    actor: ActorContext,
    annotation_id: object,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_annotate(actor)
    body = str(payload.get("body") or "").strip()
    if not body or len(body) > 20000:
        raise HTTPException(status_code=422, detail="message body must contain 1–20000 characters")
    with tenant_session(actor.tenant_id) as session:
        annotation = (
            session.execute(
                text("SELECT * FROM research.document_annotations WHERE id::text = :id"),
                {"id": str(annotation_id)},
            )
            .mappings()
            .one_or_none()
        )
        if annotation is None:
            raise HTTPException(status_code=404, detail="Document annotation not found")
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.document_annotation_messages(
                      id, tenant_id, project_id, file_id, file_version_id,
                      annotation_id, message_kind, body, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :file_id, :file_version_id,
                      :annotation_id, 'user', :body, :created_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "project_id": annotation["project_id"],
                    "file_id": annotation["file_id"],
                    "file_version_id": annotation["file_version_id"],
                    "annotation_id": annotation["id"],
                    "body": body,
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
    return {"ok": True, "message": _json_safe(dict(row))}


def set_annotation_status(
    actor: ActorContext,
    annotation_id: object,
    resolved: bool,
) -> dict[str, object]:
    _require_annotate(actor)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    UPDATE research.document_annotations
                    SET status = :state,
                        resolved_by = CASE WHEN :resolved THEN :actor_id ELSE NULL END,
                        resolved_at = CASE WHEN :resolved THEN now() ELSE NULL END
                    WHERE id::text = :id
                    RETURNING *
                    """
                ),
                {
                    "id": str(annotation_id),
                    "state": "resolved" if resolved else "open",
                    "resolved": resolved,
                    "actor_id": actor.user_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Document annotation not found")
        _audit(
            session,
            actor,
            "research.document.annotation.status_changed",
            {"annotation_id": str(annotation_id), "status": row["status"]},
        )
    return {"ok": True, "annotation": _json_safe(dict(row))}


def _query_terms(question: str) -> list[str]:
    terms = [
        item.lower()
        for item in re.findall(r"[A-Za-z0-9_\-]{2,}|[\u3400-\u9fff]{2,}", question)
    ]
    expanded: list[str] = []
    for term in terms:
        expanded.append(term)
        if re.fullmatch(r"[\u3400-\u9fff]+", term) and len(term) > 3:
            expanded.extend(term[index : index + 2] for index in range(len(term) - 1))
    return list(dict.fromkeys(expanded))[:80]


def _rank_blocks(
    blocks: list[dict[str, object]],
    index: dict[str, object],
    question: str,
    anchor: dict[str, object] | None,
) -> list[dict[str, object]]:
    scores: dict[int, float] = {}
    terms = _query_terms(question)
    question_lower = question.lower().strip()
    selected_ordinals: set[int] = set()
    if anchor:
        selected_ordinals.update(
            range(int(anchor["start_block_ordinal"]), int(anchor["end_block_ordinal"]) + 1)
        )
    for block in blocks:
        ordinal = int(block["ordinal"])
        value = str(block["content"]).lower()
        heading = " / ".join(block.get("heading_path") or []).lower()
        score = 1000.0 if ordinal in selected_ordinals else 0.0
        if question_lower and question_lower in value:
            score += 80
        for term in terms:
            if term in value:
                score += 6 + min(value.count(term), 5)
            if term in heading:
                score += 8
        if block["block_type"] in {"title", "heading"}:
            score += 0.5
        scores[ordinal] = score
    for concept in index.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        names = [str(concept.get("name") or ""), *[str(x) for x in concept.get("aliases") or []]]
        if any(name and name.lower() in question_lower for name in names):
            for ordinal in concept.get("block_ordinals") or []:
                if int(ordinal) in scores:
                    scores[int(ordinal)] += 120
    ranked = sorted(blocks, key=lambda item: (-scores[int(item["ordinal"])], int(item["ordinal"])))
    selected = [item for item in ranked if scores[int(item["ordinal"])] > 0][:10]
    if not selected:
        selected = blocks[:6]
    selected_ord = {int(item["ordinal"]) for item in selected}
    for item in list(selected):
        ordinal = int(item["ordinal"])
        for neighbor in (ordinal - 1, ordinal + 1):
            if neighbor >= 0 and neighbor not in selected_ord and neighbor < len(blocks):
                selected.append(blocks[neighbor])
                selected_ord.add(neighbor)
    return sorted(selected[:14], key=lambda item: int(item["ordinal"]))


def ask_document(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    _require_read(actor)
    question = str(payload.get("question") or "").strip()
    if not question or len(question) > 12000:
        raise HTTPException(status_code=422, detail="question must contain 1–12000 characters")
    version = int(payload["version"]) if payload.get("version") is not None else None
    project, file_row, version_row = _target_rows(actor, project_ref, file_ref, version)
    version_id = UUID(str(version_row["id"]))
    index = ensure_document_index(actor, version_id, settings)
    blocks = _blocks(actor, version_id)
    anchor = resolve_anchor(blocks, payload["anchor"]) if payload.get("anchor") else None
    relevant = _rank_blocks(blocks, index, question, anchor)
    context_lines: list[str] = []
    used = 0
    for block in relevant:
        heading = " / ".join(block.get("heading_path") or []) or "ROOT"
        line = f"[B{int(block['ordinal']):04d} | {heading}]\n{block['content']}"
        if used + len(line) > MAX_AI_CONTEXT:
            break
        context_lines.append(line)
        used += len(line)
    selection = f"\n使用者選取：{anchor['quote']}" if anchor else ""
    try:
        configured = connected_deepseek(actor, settings)
        connection = ModelConnection(
            base_url=configured.base_url,
            model=DEEPSEEK_RUNTIME_MODELS["balanced"],
            api_key=configured.api_key,
        )
        response = chat_completion(
            connection,
            system_prompt=(
                "你是論文的版本固定閱讀助手。只能依據提供的文件區塊回答；資訊不足時要明說。"
                "回答要直接、精確、適合研究者理解。輸出 JSON，包含 answer 字串與 citations 陣列；"
                "每個 citation 必須含 block（如 B0007）與該區塊中的短 quote，不得引用不存在的區塊。"
            ),
            user_prompt=(
                f"文件：{file_row['logical_path']}，版本 V{version_row['version']}。{selection}\n"
                f"問題：{question}\n\n可用證據區塊：\n" + "\n\n".join(context_lines)
            ),
            thinking=False,
            max_tokens=2_400,
            json_mode=True,
        )
        answer_payload = _parse_model_json(response)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Research AI is temporarily unavailable: {str(exc)[:300]}",
        ) from exc
    answer = str(answer_payload.get("answer") or "").strip()
    if not answer:
        raise HTTPException(status_code=502, detail="Research AI returned an empty answer")
    by_label = {f"B{int(item['ordinal']):04d}": item for item in relevant}
    citations: list[dict[str, object]] = []
    for raw in answer_payload.get("citations") or []:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("block") or "").upper()
        block = by_label.get(label)
        if not block:
            continue
        requested_quote = str(raw.get("quote") or "").strip()
        content = str(block["content"])
        quote = requested_quote if requested_quote and requested_quote in content else content[:260]
        citations.append(
            {
                "block": label,
                "block_id": str(block["id"]),
                "ordinal": int(block["ordinal"]),
                "heading_path": block.get("heading_path") or [],
                "quote": quote,
                "start_offset": int(block["start_offset"]),
                "end_offset": int(block["end_offset"]),
            }
        )
    if not citations:
        for block in relevant[:3]:
            citations.append(
                {
                    "block": f"B{int(block['ordinal']):04d}",
                    "block_id": str(block["id"]),
                    "ordinal": int(block["ordinal"]),
                    "heading_path": block.get("heading_path") or [],
                    "quote": str(block["content"])[:260],
                    "start_offset": int(block["start_offset"]),
                    "end_offset": int(block["end_offset"]),
                }
            )
    question_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO research.document_questions(
                      id, tenant_id, project_id, file_id, file_version_id,
                      question, selection_anchor, answer, citations, model, asked_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :file_id, :file_version_id,
                      :question, CAST(:selection_anchor AS jsonb), :answer,
                      CAST(:citations AS jsonb), :model, :asked_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": question_id,
                    "tenant_id": actor.tenant_id,
                    "project_id": project["id"],
                    "file_id": file_row["id"],
                    "file_version_id": version_id,
                    "question": question,
                    "selection_anchor": json.dumps(anchor, ensure_ascii=False) if anchor else None,
                    "answer": answer,
                    "citations": json.dumps(citations, ensure_ascii=False),
                    "model": connection.model,
                    "asked_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.document.question.answered",
            {
                "question_id": question_id,
                "file_version_id": version_id,
                "citation_blocks": [item["block"] for item in citations],
            },
        )
    return {"ok": True, "question": _json_safe(dict(row))}
