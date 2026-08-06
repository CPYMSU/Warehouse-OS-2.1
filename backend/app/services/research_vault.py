"""Research-object custody, preview and format-aware revision services."""

from __future__ import annotations

import csv
import difflib
import io
import json
import mimetypes
import os
import re
import sqlite3
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from xml.etree import ElementTree

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import tenant_session
from app.services.object_storage import LocalContentAddressedObjectStore, StoredObject

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings


PROJECT_STATUSES = frozenset({"draft", "active", "review", "published", "archived"})
MAX_EXTRACTED_TEXT = 1_000_000
MAX_PREVIEW_BYTES = 8 * 1024 * 1024
MAX_DIFF_ROWS = 50_000
TEXT_EXTENSIONS = frozenset(
    {
        ".txt",
        ".md",
        ".rst",
        ".tex",
        ".yaml",
        ".yml",
        ".json",
        ".xml",
        ".py",
        ".r",
        ".jl",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".swift",
        ".sh",
        ".zsh",
        ".toml",
        ".ini",
        ".cfg",
        ".env",
        ".gitignore",
    }
)
DATABASE_EXTENSIONS = frozenset({".sql", ".ddl", ".dbml", ".db", ".sqlite", ".sqlite3"})
SQLITE_EXTENSIONS = frozenset({".db", ".sqlite", ".sqlite3"})
DATASET_EXTENSIONS = frozenset({".csv", ".tsv"})
NOTEBOOK_EXTENSIONS = frozenset({".ipynb"})
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"})
PROGRAM_EXTENSIONS = frozenset(
    {
        ".py",
        ".r",
        ".jl",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".swift",
        ".sh",
        ".zsh",
    }
)


def research_asset_class(logical_path: object, file_kind: object) -> str:
    """Classify a research object by scholarly purpose, independently of its format."""

    normalized = str(logical_path or "").strip().replace("\\", "/").lower()
    path = PurePosixPath(normalized or "unnamed")
    extension = Path(path.name).suffix.lower()
    parts = {part for part in path.parts if part not in {"", "."}}
    stem_tokens = set(filter(None, re.split(r"[^a-z0-9]+", path.stem)))
    tokens = parts | stem_tokens
    kind = str(file_kind or "").lower()

    # Executable source always stays code, even when it generates figures or reports.
    if extension in PROGRAM_EXTENSIONS:
        return "code"
    if kind == "database" or extension in DATABASE_EXTENSIONS:
        return "database"
    if kind == "notebook" or extension in NOTEBOOK_EXTENSIONS:
        return "notebook"
    if kind == "image" or extension in IMAGE_EXTENSIONS:
        return "figure"
    if kind == "dataset" or extension in DATASET_EXTENSIONS:
        return "dataset"

    if tokens & {
        "administration",
        "admin",
        "governance",
        "manifest",
        "metadata",
        "license",
        "licenses",
        "dmp",
        "protocol",
        "config",
        "configuration",
    } or path.name.startswith(("readme", "license", "changelog")):
        return "administration"
    if tokens & {
        "literature",
        "reference",
        "references",
        "bibliography",
        "bibliographic",
        "citation",
        "citations",
        "sources",
    }:
        return "literature"
    if tokens & {
        "manuscript",
        "article",
        "thesis",
        "dissertation",
        "submission",
        "preprint",
        "draft",
    }:
        return "manuscript"
    if tokens & {
        "data",
        "dataset",
        "datasets",
        "observations",
        "results",
        "outputs",
        "inputs",
    } or extension in {".json", ".jsonl", ".ndjson", ".parquet", ".arrow"}:
        return "dataset"
    if kind == "code":
        administrative_extensions = {
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".env",
            ".xml",
        }
        return "administration" if extension in administrative_extensions else "code"
    if kind in {"document", "html", "pdf"}:
        return "manuscript"
    return "other"


@dataclass(frozen=True)
class PreviewAnalysis:
    file_kind: str
    extracted_text: str | None
    preview: dict[str, object]


class _VisibleHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "template", "noscript"}:
            self.hidden_depth += 1
        if not self.hidden_depth and tag.lower() in {
            "p",
            "div",
            "section",
            "article",
            "br",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "template", "noscript"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        elif not self.hidden_depth and tag.lower() in {
            "p",
            "div",
            "section",
            "article",
            "li",
            "tr",
        }:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth and data.strip():
            self.parts.append(data)

    def text(self) -> str:
        lines = (" ".join(part.split()) for part in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line).strip()


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _require_read(actor: ActorContext) -> None:
    if "research.read" in actor.permissions:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Research read permission denied"
    )


def _require_write(actor: ActorContext) -> None:
    if "research.write" in actor.permissions:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Research write permission denied"
    )


def require_research_write(actor: ActorContext) -> None:
    """Authorize a write before the API accepts a potentially large stream."""

    _require_write(actor)


def _audit(
    session: Session, actor: ActorContext, event_type: str, payload: dict[str, object]
) -> None:
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
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _slug(value: object) -> str:
    candidate = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")[:63]
    if len(candidate) < 2:
        candidate = f"research-{candidate or uuid4().hex[:8]}"
    return candidate.rstrip("-")


def _uuid(value: object) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _logical_path(value: object, filename: str) -> str:
    raw = str(value or filename).strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if (
        not raw
        or raw.startswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
        or len(raw) > 500
    ):
        raise HTTPException(status_code=422, detail="logical_path must be a safe relative path")
    return str(path)


def _file_kind(filename: str, content_type: str | None) -> str:
    extension = Path(filename).suffix.lower()
    media_type = str(content_type or "").lower().split(";", 1)[0]
    if extension == ".pdf" or media_type == "application/pdf":
        return "pdf"
    if extension in {".docx", ".odt", ".rtf"} or media_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/rtf",
    }:
        return "document"
    if extension in {".html", ".htm"} or media_type == "text/html":
        return "html"
    if extension in DATASET_EXTENSIONS:
        return "dataset"
    if extension in DATABASE_EXTENSIONS:
        return "database"
    if extension in NOTEBOOK_EXTENSIONS:
        return "notebook"
    if extension in IMAGE_EXTENSIONS or media_type.startswith("image/"):
        return "image"
    if extension in TEXT_EXTENSIONS or media_type.startswith("text/"):
        return "code" if extension not in {".txt", ".md", ".rst", ".tex"} else "document"
    return "binary"


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "gb18030", "big5"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{namespace}p"):
        value = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t")).strip()
        if value:
            paragraphs.append(value)
    return "\n".join(paragraphs)


def _pdf_text(path: Path) -> tuple[str, int]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", 0
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages[:100]:
        pages.append(page.extract_text() or "")
        if sum(len(item) for item in pages) >= MAX_EXTRACTED_TEXT:
            break
    return "\n\n".join(pages), len(reader.pages)


def _csv_rows(text_value: str, *, extension: str, limit: int = 250) -> dict[str, object]:
    delimiter = "\t" if extension == ".tsv" else ","
    reader = csv.reader(io.StringIO(text_value), delimiter=delimiter)
    rows: list[list[str]] = []
    for index, row in enumerate(reader):
        rows.append([str(value) for value in row])
        if index >= limit:
            break
    columns = rows[0] if rows else []
    body = rows[1:] if rows else []
    width = len(columns)
    normalized = [row[:width] + [""] * max(0, width - len(row)) for row in body]
    return {
        "columns": columns,
        "rows": normalized,
        "preview_rows": len(normalized),
        "truncated": len(rows) > limit,
    }


def _sqlite_preview(path: Path) -> tuple[str, dict[str, object]]:
    connection = sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro&immutable=1",
        uri=True,
        timeout=2,
    )
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        definitions = connection.execute(
            """
            SELECT name, type, sql
            FROM sqlite_master
            WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            LIMIT 21
            """
        ).fetchall()
        tables: list[dict[str, object]] = []
        text_sections: list[str] = []
        for definition in definitions[:20]:
            name = str(definition["name"])
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [
                str(row["name"])
                for row in connection.execute(f"PRAGMA table_info({quoted})").fetchall()
            ]
            sample_rows: list[list[object]] = []
            if definition["type"] == "table":
                for row in connection.execute(f"SELECT * FROM {quoted} LIMIT 50").fetchall():
                    sample_rows.append(
                        [
                            f"<BLOB {len(value)} bytes>" if isinstance(value, bytes) else value
                            for value in row
                        ]
                    )
            tables.append(
                {
                    "name": name,
                    "type": definition["type"],
                    "columns": columns,
                    "rows": sample_rows,
                    "sample_rows": len(sample_rows),
                }
            )
            text_sections.append(
                "\n".join(
                    [
                        f"## {definition['type']} {name}",
                        str(definition["sql"] or ""),
                        json.dumps(
                            {"columns": columns, "sample_rows": sample_rows},
                            ensure_ascii=False,
                            default=str,
                            sort_keys=True,
                        ),
                    ]
                )
            )
        return "\n\n".join(text_sections), {
            "renderer": "database",
            "tables": tables,
            "table_count": len(definitions),
            "truncated": len(definitions) > 20,
        }
    finally:
        connection.close()


def analyse_object(
    path: Path, filename: str, content_type: str | None, size_bytes: int
) -> PreviewAnalysis:
    kind = _file_kind(filename, content_type)
    extension = Path(filename).suffix.lower()
    preview: dict[str, object] = {"mode": kind, "extension": extension, "available": True}
    extracted: str | None = None
    try:
        if kind == "pdf":
            if size_bytes <= 80 * 1024 * 1024:
                extracted, pages = _pdf_text(path)
                preview.update({"pages": pages or None, "text_extracted": bool(extracted)})
            else:
                preview.update(
                    {"text_extracted": False, "reason": "pdf_too_large_for_text_extraction"}
                )
        elif kind == "document" and extension == ".docx":
            extracted = _docx_text(path)
            preview.update(
                {"paragraphs": len(extracted.splitlines()), "renderer": "structured_text"}
            )
        elif kind == "database" and extension in SQLITE_EXTENSIONS:
            extracted, database_preview = _sqlite_preview(path)
            preview.update(database_preview)
        elif kind in {"document", "code", "database", "html", "notebook", "dataset"}:
            with path.open("rb") as source:
                data = source.read(MAX_PREVIEW_BYTES + 1)
            truncated = len(data) > MAX_PREVIEW_BYTES
            raw = _decode(data[:MAX_PREVIEW_BYTES])
            if kind == "html":
                parser = _VisibleHTML()
                parser.feed(raw)
                extracted = parser.text()
                preview.update({"renderer": "sandboxed_html", "truncated": truncated})
            elif kind == "notebook":
                payload = json.loads(raw)
                cells = payload.get("cells") if isinstance(payload, dict) else []
                lines: list[str] = []
                for index, cell in enumerate(cells if isinstance(cells, list) else []):
                    source = cell.get("source") if isinstance(cell, dict) else []
                    body = "".join(source) if isinstance(source, list) else str(source or "")
                    lines.append(
                        f"## cell {index + 1} [{cell.get('cell_type', 'unknown')}]\n{body}"
                    )
                extracted = "\n\n".join(lines)
                preview.update({"renderer": "notebook", "cells": len(cells or [])})
            else:
                extracted = raw
                preview.update(
                    {
                        "renderer": "data_grid" if kind == "dataset" else "text",
                        "truncated": truncated,
                    }
                )
                if kind == "dataset":
                    preview.update(_csv_rows(raw, extension=extension))
        elif kind == "image":
            preview.update({"renderer": "image"})
        else:
            preview.update({"available": False, "renderer": "metadata"})
    except (
        OSError,
        ValueError,
        KeyError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
        sqlite3.DatabaseError,
    ) as exc:
        preview.update({"available": False, "reason": type(exc).__name__})
        extracted = None
    if extracted is not None:
        extracted = extracted[:MAX_EXTRACTED_TEXT]
        preview["characters"] = len(extracted)
    return PreviewAnalysis(file_kind=kind, extracted_text=extracted, preview=preview)


class ResearchGitRepository:
    """Native Git ledger that commits content-addressed research manifests."""

    def __init__(self, root: Path, tenant_id: UUID, project_id: UUID) -> None:
        base = root.expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = base / "tenants" / str(tenant_id) / "projects" / str(project_id)

    def _run(self, *args: str, env: dict[str, str] | None = None) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.path), *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
                env=env,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            detail = getattr(exc, "stderr", None) or str(exc)
            raise HTTPException(
                status_code=503, detail=f"Research Git ledger unavailable: {detail}"
            ) from exc
        return result.stdout.strip()

    def commit(
        self,
        *,
        branch: str,
        message: str,
        manifest: dict[str, object],
        author_name: str,
        author_email: str,
    ) -> tuple[str, str | None]:
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not (self.path / ".git").is_dir():
            try:
                subprocess.run(
                    ["git", "init", "-b", branch, str(self.path)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise HTTPException(
                    status_code=503, detail="Research Git repository could not be initialized"
                ) from exc
            (self.path / ".gitattributes").write_text(
                "research-manifest.json text eol=lf\n", encoding="utf-8"
            )
        parent = None
        try:
            parent = self._run("rev-parse", "HEAD") or None
        except HTTPException:
            parent = None
        (self.path / "research-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        self._run("add", "--", ".gitattributes", "research-manifest.json")
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": author_name or "Warehouse OS Research",
                "GIT_AUTHOR_EMAIL": author_email
                if "@" in author_email
                else "research@warehouse.local",
                "GIT_COMMITTER_NAME": "Warehouse OS Research Vault",
                "GIT_COMMITTER_EMAIL": "research@warehouse.local",
            }
        )
        self._run("commit", "--allow-empty", "--quiet", "-m", message, env=environment)
        return self._run("rev-parse", "HEAD"), parent


def _project_row(session: Session, project_ref: object, *, lock: bool = False) -> dict[str, object]:
    project_id = _uuid(project_ref)
    clause = "id = :project_id" if project_id else "slug = :slug"
    params = {"project_id": project_id} if project_id else {"slug": str(project_ref).strip()}
    suffix = " FOR UPDATE" if lock else ""
    row = (
        session.execute(text(f"SELECT * FROM research.projects WHERE {clause}{suffix}"), params)
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    return dict(row)


def _file_row(session: Session, project_id: UUID, file_ref: object) -> dict[str, object]:
    file_id = _uuid(file_ref)
    clause = "id = :file_id" if file_id else "logical_path = :logical_path"
    params = (
        {"project_id": project_id, "file_id": file_id}
        if file_id
        else {"project_id": project_id, "logical_path": str(file_ref).strip()}
    )
    row = (
        session.execute(
            text(
                f"SELECT * FROM research.files "
                f"WHERE project_id = :project_id AND {clause}"
            ),
            params,
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Research file not found")
    return dict(row)


def _public_project(row: dict[str, object]) -> dict[str, object]:
    return _json_safe({**row, "metadata": row.get("metadata") or {}})


def _public_version(row: dict[str, object], *, include_preview: bool = True) -> dict[str, object]:
    payload = {
        "id": row["id"],
        "version": row["version"],
        "filename": row["original_filename"],
        "content_type": row["content_type"],
        "content_sha256": row["content_sha256"],
        "size_bytes": row["size_bytes"],
        "preview_available": bool(row.get("preview_available") or row.get("preview")),
        "git_sha": row.get("git_sha"),
        "commit_message": row.get("commit_message"),
        "created_by": row.get("created_by"),
        "created_at": row.get("created_at"),
    }
    if include_preview:
        payload["preview"] = row.get("preview") or {}
    return _json_safe(payload)


def _public_file(row: dict[str, object]) -> dict[str, object]:
    public = dict(row)
    public["asset_class"] = research_asset_class(
        public.get("logical_path"), public.get("file_kind")
    )
    return _json_safe(public)


def _manifest(session: Session, project: dict[str, object]) -> dict[str, object]:
    rows = (
        session.execute(
            text(
                """
            SELECT f.logical_path, f.display_name, f.file_kind,
                   v.version, v.content_sha256, v.size_bytes, v.content_type
            FROM research.files AS f
            JOIN LATERAL (
              SELECT * FROM research.file_versions
              WHERE file_id = f.id ORDER BY version DESC LIMIT 1
            ) AS v ON true
            WHERE f.project_id = :project_id AND f.status = 'active'
            ORDER BY f.logical_path
            """
            ),
            {"project_id": project["id"]},
        )
        .mappings()
        .all()
    )
    return {
        "schema": "warehouse-research-manifest/v1",
        "project": {"id": str(project["id"]), "slug": project["slug"], "title": project["title"]},
        "branch": project["default_branch"],
        "files": [
            {
                **_json_safe(dict(row)),
                "asset_class": research_asset_class(row["logical_path"], row["file_kind"]),
            }
            for row in rows
        ],
    }


def _record_commit(
    session: Session,
    actor: ActorContext,
    settings: Settings,
    project: dict[str, object],
    message: str,
) -> tuple[str, str | None, dict[str, object]]:
    manifest = _manifest(session, project)
    git_sha, parent = ResearchGitRepository(
        settings.research_repository_root, actor.tenant_id, project["id"]
    ).commit(
        branch=str(project["default_branch"]),
        message=message,
        manifest=manifest,
        author_name=actor.display_name,
        author_email=actor.username,
    )
    session.execute(
        text(
            """
            INSERT INTO research.commits(
              id, tenant_id, project_id, git_sha, parent_git_sha,
              branch_name, message, manifest, created_by
            ) VALUES (
              :id, :tenant_id, :project_id, :git_sha, :parent_git_sha,
              :branch_name, :message, CAST(:manifest AS jsonb), :created_by
            )
            """
        ),
        {
            "id": uuid4(),
            "tenant_id": actor.tenant_id,
            "project_id": project["id"],
            "git_sha": git_sha,
            "parent_git_sha": parent,
            "branch_name": project["default_branch"],
            "message": message,
            "manifest": json.dumps(manifest, ensure_ascii=False),
            "created_by": actor.user_id,
        },
    )
    session.execute(
        text("UPDATE research.projects SET head_git_sha = :git_sha WHERE id = :project_id"),
        {"git_sha": git_sha, "project_id": project["id"]},
    )
    return git_sha, parent, manifest


def list_projects(actor: ActorContext) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT p.*,
                       (SELECT count(*) FROM research.files f
                        WHERE f.project_id = p.id AND f.status = 'active')::integer AS file_count,
                       (SELECT count(*) FROM research.file_versions v
                        WHERE v.project_id = p.id)::integer AS version_count,
                       (SELECT count(*) FROM research.commits c
                        WHERE c.project_id = p.id)::integer AS commit_count,
                       (SELECT COALESCE(sum(v.size_bytes), 0)
                        FROM research.file_versions v WHERE v.project_id = p.id) AS stored_bytes
                FROM research.projects p
                ORDER BY p.updated_at DESC, p.title
                """
                )
            )
            .mappings()
            .all()
        )
    projects = [_public_project(dict(row)) for row in rows]
    return {
        "source": "research_postgresql_git",
        "projects": projects,
        "total": len(projects),
        "capabilities": {
            "inline_preview": True,
            "git_commits": True,
            "semantic_diff": True,
            "content_addressed_storage": True,
            "version_pinned_annotations": True,
            "grounded_document_ai": True,
        },
    }


def create_project(
    actor: ActorContext, payload: dict[str, object], settings: Settings
) -> dict[str, object]:
    _require_write(actor)
    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")
    project_status = str(payload.get("status") or "active")
    if project_status not in PROJECT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid research project status")
    project_id = uuid4()
    project_slug = _slug(payload.get("slug") or title)
    with tenant_session(actor.tenant_id) as session:
        duplicate = session.execute(
            text("SELECT 1 FROM research.projects WHERE slug = :slug"), {"slug": project_slug}
        ).scalar_one_or_none()
        if duplicate:
            project_slug = f"{project_slug[:54]}-{project_id.hex[:8]}"
        row = (
            session.execute(
                text(
                    """
                INSERT INTO research.projects(
                  id, tenant_id, slug, title, summary, research_area,
                  status, metadata, created_by
                ) VALUES (
                  :id, :tenant_id, :slug, :title, :summary, :research_area,
                  :status, CAST(:metadata AS jsonb), :created_by
                ) RETURNING *
                """
                ),
                {
                    "id": project_id,
                    "tenant_id": actor.tenant_id,
                    "slug": project_slug,
                    "title": title,
                    "summary": str(payload.get("summary") or "").strip() or None,
                    "research_area": str(payload.get("research_area") or "").strip() or None,
                    "status": project_status,
                    "metadata": json.dumps(
                        payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
                    ),
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        project = dict(row)
        git_sha, _, _ = _record_commit(
            session, actor, settings, project, "Initialize research project"
        )
        _audit(
            session,
            actor,
            "research.project.created",
            {"project_id": project_id, "slug": project_slug, "git_sha": git_sha},
        )
        project["head_git_sha"] = git_sha
    return {"ok": True, "project": _public_project(project)}


def project_detail(actor: ActorContext, project_ref: object) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        files = (
            session.execute(
                text(
                    """
                SELECT f.*, latest.version AS current_version,
                       latest.content_type, latest.content_sha256,
                       latest.size_bytes, latest.git_sha, latest.preview_available,
                       latest.created_at AS version_created_at,
                       (SELECT count(*) FROM research.file_versions all_versions
                        WHERE all_versions.file_id = f.id)::integer AS version_count
                FROM research.files f
                JOIN LATERAL (
                  SELECT version, content_type, content_sha256, size_bytes, git_sha,
                         created_at,
                         (preview IS NOT NULL AND preview <> '{}'::jsonb) AS preview_available
                  FROM research.file_versions
                  WHERE file_id = f.id ORDER BY version DESC LIMIT 1
                ) latest ON true
                WHERE f.project_id = :project_id AND f.status = 'active'
                ORDER BY f.logical_path
                """
                ),
                {"project_id": project["id"]},
            )
            .mappings()
            .all()
        )
        versions = (
            session.execute(
                text(
                    """
                SELECT v.id, v.file_id, v.version, v.original_filename,
                       v.content_type, v.content_sha256, v.size_bytes, v.git_sha,
                       v.commit_message, v.created_by, v.created_at,
                       (v.preview IS NOT NULL AND v.preview <> '{}'::jsonb) AS preview_available
                FROM research.file_versions v
                WHERE v.project_id = :project_id
                ORDER BY v.file_id, v.version DESC
                """
                ),
                {"project_id": project["id"]},
            )
            .mappings()
            .all()
        )
        commits = (
            session.execute(
                text(
                    """
                SELECT c.git_sha, c.parent_git_sha, c.branch_name, c.message,
                       c.created_by, c.created_at, u.display_name AS author_name
                FROM research.commits c
                LEFT JOIN iam.users u ON u.id = c.created_by
                WHERE c.project_id = :project_id
                ORDER BY c.created_at DESC LIMIT 80
                """
                ),
                {"project_id": project["id"]},
            )
            .mappings()
            .all()
        )
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in versions:
        grouped.setdefault(str(row["file_id"]), []).append(
            _public_version(dict(row), include_preview=False)
        )
    public_files = []
    for row in files:
        item = _public_file(dict(row))
        item["versions"] = grouped.get(str(row["id"]), [])
        public_files.append(item)
    return {
        "source": "research_postgresql_git",
        "project": _public_project(project),
        "files": public_files,
        "commits": [_json_safe(dict(row)) for row in commits],
    }


def research_formats(actor: ActorContext, settings: Settings) -> dict[str, object]:
    """Describe the live custody and preview contract without inventing sample data."""

    _require_read(actor)
    return {
        "source": "research_runtime_contract",
        "upload": {
            "protocol": "multipart/form-data",
            "max_bytes": settings.research_max_upload_bytes,
            "checksum": "sha256",
            "content_addressed": True,
            "creates_file_version": True,
            "creates_git_commit": True,
        },
        "formats": [
            {
                "kind": "document",
                "extensions": [".docx", ".txt", ".md", ".rst", ".tex"],
                "preview": "openxml_html_mathml_and_structured_text",
                "diff": "semantic_text",
                "review": "character_anchors_annotations_and_grounded_ai",
            },
            {
                "kind": "pdf",
                "extensions": [".pdf"],
                "preview": "inline_pdf_and_extracted_text",
                "diff": "semantic_text_or_binary",
            },
            {
                "kind": "html",
                "extensions": [".html", ".htm"],
                "preview": "sandboxed_html",
                "diff": "semantic_text",
            },
            {
                "kind": "dataset",
                "extensions": sorted(DATASET_EXTENSIONS),
                "preview": "data_grid",
                "diff": "row_level",
            },
            {
                "kind": "database",
                "extensions": sorted(DATABASE_EXTENSIONS),
                "preview": "schema_and_read_only_samples",
                "diff": "semantic_text_or_binary",
            },
            {
                "kind": "notebook",
                "extensions": sorted(NOTEBOOK_EXTENSIONS),
                "preview": "notebook_cells",
                "diff": "semantic_text",
            },
            {
                "kind": "image",
                "extensions": sorted(IMAGE_EXTENSIONS),
                "preview": "inline_image",
                "diff": "checksum",
            },
            {
                "kind": "code",
                "extensions": sorted(
                    extension
                    for extension in TEXT_EXTENSIONS
                    if extension not in {".txt", ".md", ".rst", ".tex"}
                ),
                "preview": "source_text",
                "diff": "unified_text",
            },
        ],
    }


def upload_contract(
    actor: ActorContext,
    project_ref: object,
    settings: Settings,
) -> dict[str, object]:
    """Return a safe, concrete terminal upload contract for one project."""

    _require_write(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
    path = f"/api/research/projects/{project['id']}/files"
    return {
        "source": "research_runtime_contract",
        "project": {
            "id": str(project["id"]),
            "slug": project["slug"],
            "title": project["title"],
        },
        "request": {
            "method": "POST",
            "path": path,
            "content_type": "multipart/form-data",
            "runtime_scope": "research",
            "max_bytes": settings.research_max_upload_bytes,
            "fields": {
                "file": {"type": "binary", "required": True},
                "logical_path": {"type": "string", "required": False},
                "commit_message": {"type": "string", "required": False},
                "expected_sha256": {"type": "sha256", "required": False},
            },
        },
        "effects": [
            "sha256_verified_content_addressed_storage",
            "immutable_file_version",
            "native_git_commit",
            "tenant_audit_event",
        ],
        "curl_template": (
            f'curl --fail-with-body -X POST "$WAREHOUSE_BASE_URL{path}" '
            '-H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY" '
            '-F "file=@./PATH_TO_FILE" '
            '-F "logical_path=manuscript/PATH_TO_FILE" '
            '-F "commit_message=Describe this revision"'
        ),
    }


def file_versions(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        file_row = _file_row(session, project["id"], file_ref)
        versions = (
            session.execute(
                text(
                    """
                    SELECT * FROM research.file_versions
                    WHERE project_id = :project_id AND file_id = :file_id
                    ORDER BY version DESC
                    """
                ),
                {"project_id": project["id"], "file_id": file_row["id"]},
            )
            .mappings()
            .all()
        )
    return {
        "source": "research_postgresql_git",
        "project": _public_project(project),
        "file": _public_file(file_row),
        "versions": [_public_version(dict(row)) for row in versions],
        "total": len(versions),
    }


def project_commits(
    actor: ActorContext,
    project_ref: object,
    limit: int = 80,
) -> dict[str, object]:
    _require_read(actor)
    maximum = max(1, min(int(limit), 200))
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        commits = (
            session.execute(
                text(
                    """
                    SELECT c.git_sha, c.parent_git_sha, c.branch_name, c.message,
                           c.manifest, c.created_by, c.created_at,
                           u.display_name AS author_name
                    FROM research.commits c
                    LEFT JOIN iam.users u ON u.id = c.created_by
                    WHERE c.project_id = :project_id
                    ORDER BY c.created_at DESC
                    LIMIT :limit
                    """
                ),
                {"project_id": project["id"], "limit": maximum},
            )
            .mappings()
            .all()
        )
    return {
        "source": "research_postgresql_git",
        "project": _public_project(project),
        "branch": project["default_branch"],
        "head_git_sha": project.get("head_git_sha"),
        "commits": [_json_safe(dict(row)) for row in commits],
        "total": len(commits),
        "limit": maximum,
    }


def add_file_version(
    actor: ActorContext,
    project_ref: object,
    *,
    stored: StoredObject,
    store: LocalContentAddressedObjectStore,
    original_filename: str,
    content_type: str | None,
    logical_path: str | None,
    commit_message: str | None,
    settings: Settings,
) -> dict[str, object]:
    _require_write(actor)
    safe_filename = Path(original_filename or "research-file").name or "research-file"
    path_value = _logical_path(logical_path, safe_filename)
    media_type = (
        content_type or mimetypes.guess_type(safe_filename)[0] or "application/octet-stream"
    )
    analysis = analyse_object(
        store.path_for(stored.object_key), safe_filename, media_type, stored.size_bytes
    )
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref, lock=True)
        file_row = (
            session.execute(
                text(
                    """
                    SELECT * FROM research.files
                    WHERE project_id = :project_id AND logical_path = :logical_path
                    FOR UPDATE
                    """
                ),
                {"project_id": project["id"], "logical_path": path_value},
            )
            .mappings()
            .one_or_none()
        )
        if file_row is None:
            file_id = uuid4()
            file_row = (
                session.execute(
                    text(
                        """
                    INSERT INTO research.files(
                      id, tenant_id, project_id, logical_path, display_name,
                      file_kind, created_by
                    ) VALUES (
                      :id, :tenant_id, :project_id, :logical_path, :display_name,
                      :file_kind, :created_by
                    ) RETURNING *
                    """
                    ),
                    {
                        "id": file_id,
                        "tenant_id": actor.tenant_id,
                        "project_id": project["id"],
                        "logical_path": path_value,
                        "display_name": safe_filename,
                        "file_kind": analysis.file_kind,
                        "created_by": actor.user_id,
                    },
                )
                .mappings()
                .one()
            )
        else:
            file_id = file_row["id"]
            session.execute(
                text(
                    """
                    UPDATE research.files
                    SET display_name = :display_name, file_kind = :file_kind
                    WHERE id = :file_id
                    """
                ),
                {
                    "display_name": safe_filename,
                    "file_kind": analysis.file_kind,
                    "file_id": file_id,
                },
            )
        version_no = int(
            session.execute(
                text(
                    """
                    SELECT COALESCE(max(version), 0) + 1
                    FROM research.file_versions
                    WHERE file_id = :file_id
                    """
                ),
                {"file_id": file_id},
            ).scalar_one()
        )
        version_id = uuid4()
        message = str(commit_message or f"Update {path_value} to v{version_no}").strip()[:500]
        session.execute(
            text(
                """
                INSERT INTO research.file_versions(
                  id, tenant_id, project_id, file_id, version, original_filename,
                  content_type, storage_provider, object_key, content_sha256,
                  size_bytes, extracted_text, preview, commit_message, created_by
                ) VALUES (
                  :id, :tenant_id, :project_id, :file_id, :version, :original_filename,
                  :content_type, :storage_provider, :object_key, :content_sha256,
                  :size_bytes, :extracted_text, CAST(:preview AS jsonb), :commit_message,
                  :created_by
                )
                """
            ),
            {
                "id": version_id,
                "tenant_id": actor.tenant_id,
                "project_id": project["id"],
                "file_id": file_id,
                "version": version_no,
                "original_filename": safe_filename,
                "content_type": media_type,
                "storage_provider": stored.provider_key,
                "object_key": stored.object_key,
                "content_sha256": stored.sha256,
                "size_bytes": stored.size_bytes,
                "extracted_text": analysis.extracted_text,
                "preview": json.dumps(analysis.preview, ensure_ascii=False),
                "commit_message": message,
                "created_by": actor.user_id,
            },
        )
        git_sha, _, _ = _record_commit(session, actor, settings, project, message)
        version = (
            session.execute(
                text(
                    """
                    UPDATE research.file_versions
                    SET git_sha = :git_sha
                    WHERE id = :version_id
                    RETURNING *
                    """
                ),
                {"git_sha": git_sha, "version_id": version_id},
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "research.file.versioned",
            {
                "project_id": project["id"],
                "file_id": file_id,
                "logical_path": path_value,
                "version": version_no,
                "git_sha": git_sha,
                "content_sha256": stored.sha256,
            },
        )
    return {
        "ok": True,
        "project_id": str(project["id"]),
        "file": _public_file({**dict(file_row), "file_kind": analysis.file_kind}),
        "version": _public_version(dict(version)),
        "git": {"sha": git_sha, "branch": project["default_branch"]},
    }


def _version_row(
    session: Session, project_id: UUID, file_id: UUID, version: int | None
) -> dict[str, object]:
    condition = "AND version = :version" if version is not None else ""
    params: dict[str, object] = {"project_id": project_id, "file_id": file_id}
    if version is not None:
        params["version"] = version
    row = (
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
    if row is None:
        raise HTTPException(status_code=404, detail="Research file version not found")
    return dict(row)


def preview_file(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    version: int | None,
    settings: Settings,
) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        file_row = _file_row(session, project["id"], file_ref)
        version_row = _version_row(session, project["id"], file_row["id"], version)
    store = LocalContentAddressedObjectStore(settings.asset_storage_root)
    path = store.path_for(str(version_row["object_key"]))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Research object is unavailable")
    analysis = analyse_object(
        path,
        str(version_row["original_filename"]),
        str(version_row["content_type"]),
        int(version_row["size_bytes"]),
    )
    result: dict[str, object] = {
        "file": _public_file(file_row),
        "version": _public_version(version_row),
        "mode": analysis.file_kind,
        "metadata": analysis.preview,
        "content_url": (
            f"/api/research/projects/{project['id']}/files/{file_row['id']}/content"
            f"?version={version_row['version']}"
        ),
    }
    if analysis.file_kind == "dataset" and analysis.extracted_text is not None:
        result["table"] = _csv_rows(
            analysis.extracted_text,
            extension=Path(str(version_row["original_filename"])).suffix.lower(),
        )
    elif analysis.file_kind in {"document", "code", "database", "notebook", "pdf"}:
        result["text"] = analysis.extracted_text or ""
    elif analysis.file_kind == "html":
        with path.open("rb") as source:
            result["html"] = _decode(source.read(MAX_PREVIEW_BYTES))
        result["text"] = analysis.extracted_text or ""
    return result


def content_descriptor(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    version: int | None,
    settings: Settings,
) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        file_row = _file_row(session, project["id"], file_ref)
        version_row = _version_row(session, project["id"], file_row["id"], version)
    if version_row["storage_provider"] != "content_addressed_local":
        raise HTTPException(status_code=409, detail="Research object uses an external provider")
    store = LocalContentAddressedObjectStore(settings.asset_storage_root)
    path = store.path_for(str(version_row["object_key"]))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Research object is unavailable")
    return {
        "path": path,
        "filename": version_row["original_filename"],
        "content_type": version_row["content_type"],
        "content_sha256": version_row["content_sha256"],
    }


def _tabular_diff(before: Path, after: Path, filename: str) -> dict[str, object]:
    extension = Path(filename).suffix.lower()
    delimiter = "\t" if extension == ".tsv" else ","

    def load(path: Path) -> tuple[list[str], dict[str, list[str]], bool]:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
            reader = csv.reader(source, delimiter=delimiter)
            columns = next(reader, [])
            keyed: dict[str, list[str]] = {}
            truncated = False
            for index, row in enumerate(reader, start=1):
                if index > MAX_DIFF_ROWS:
                    truncated = True
                    break
                base_key = row[0] if row else f"__row_{index}"
                key = base_key
                collision = 1
                while key in keyed:
                    collision += 1
                    key = f"{base_key}#{collision}"
                keyed[key] = row
        return columns, keyed, truncated

    before_columns, before_rows, before_truncated = load(before)
    after_columns, after_rows, after_truncated = load(after)
    before_keys, after_keys = set(before_rows), set(after_rows)
    changed = []
    for key in sorted(before_keys & after_keys):
        if before_rows[key] != after_rows[key]:
            changed.append({"key": key, "before": before_rows[key], "after": after_rows[key]})
    return {
        "mode": "tabular",
        "key_column": (after_columns or before_columns or ["row"])[0],
        "columns_before": before_columns,
        "columns_after": after_columns,
        "added": [
            {"key": key, "row": after_rows[key]} for key in sorted(after_keys - before_keys)[:250]
        ],
        "removed": [
            {"key": key, "row": before_rows[key]} for key in sorted(before_keys - after_keys)[:250]
        ],
        "changed": changed[:250],
        "summary": {
            "added": len(after_keys - before_keys),
            "removed": len(before_keys - after_keys),
            "changed": len(changed),
        },
        "truncated": before_truncated or after_truncated,
        "row_limit": MAX_DIFF_ROWS,
    }


def diff_file(
    actor: ActorContext,
    project_ref: object,
    file_ref: object,
    from_version: int | None,
    to_version: int | None,
    settings: Settings,
) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        project = _project_row(session, project_ref)
        file_row = _file_row(session, project["id"], file_ref)
        all_versions = [
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT * FROM research.file_versions
                    WHERE file_id = :file_id
                    ORDER BY version DESC
                    """
                ),
                {"file_id": file_row["id"]},
            )
            .mappings()
            .all()
        ]
    if len(all_versions) < 2 and (from_version is None or to_version is None):
        return {
            "available": False,
            "reason": "first_version_has_no_predecessor",
            "file": _public_file(file_row),
        }
    by_number = {int(row["version"]): row for row in all_versions}
    target_no = to_version if to_version is not None else int(all_versions[0]["version"])
    source_no = from_version if from_version is not None else target_no - 1
    before = by_number.get(source_no)
    after = by_number.get(target_no)
    if before is None or after is None or source_no == target_no:
        raise HTTPException(status_code=422, detail="Invalid research diff version range")
    store = LocalContentAddressedObjectStore(settings.asset_storage_root)
    before_path = store.path_for(str(before["object_key"]))
    after_path = store.path_for(str(after["object_key"]))
    if not before_path.is_file() or not after_path.is_file():
        raise HTTPException(status_code=404, detail="Research diff object is unavailable")
    if file_row["file_kind"] == "dataset":
        diff: dict[str, object] = _tabular_diff(
            before_path, after_path, str(after["original_filename"])
        )
    else:
        before_text = str(before.get("extracted_text") or "")
        after_text = str(after.get("extracted_text") or "")
        if before_text or after_text:
            lines = list(
                difflib.unified_diff(
                    before_text.splitlines(),
                    after_text.splitlines(),
                    fromfile=f"v{source_no}/{before['original_filename']}",
                    tofile=f"v{target_no}/{after['original_filename']}",
                    lineterm="",
                    n=3,
                )
            )
            diff = {
                "mode": "semantic_text",
                "lines": lines[:5000],
                "truncated": len(lines) > 5000,
                "summary": {
                    "added": sum(
                        1 for line in lines if line.startswith("+") and not line.startswith("+++")
                    ),
                    "removed": sum(
                        1 for line in lines if line.startswith("-") and not line.startswith("---")
                    ),
                },
            }
        else:
            diff = {
                "mode": "binary",
                "changed": before["content_sha256"] != after["content_sha256"],
                "summary": {
                    "before_bytes": before["size_bytes"],
                    "after_bytes": after["size_bytes"],
                },
            }
    return {
        "available": True,
        "file": _public_file(file_row),
        "from": _public_version(before),
        "to": _public_version(after),
        "git": {"from": before.get("git_sha"), "to": after.get("git_sha")},
        "diff": diff,
    }
