"""Tenant-scoped, read-only editions of the owner's research reading site."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path, PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/research/showcase", tags=["research-showcase"])


def _root(actor: ActorContext, settings: Settings) -> Path:
    if "research.read" not in actor.permissions:
        raise HTTPException(403, "Research read permission required")
    return (settings.research_repository_root / str(actor.tenant_id) / "_showcase").resolve()


def _catalog(root: Path) -> dict:
    path = root / "catalog.json"
    if not path.is_file():
        return {"available": False, "groups": [], "documents": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise HTTPException(503, "Research edition is temporarily unavailable") from exc


@router.get("")
def showcase_catalog(
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    response: Response,
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return _catalog(_root(actor, settings))


@router.get("/content/{logical_path:path}")
def showcase_content(
    logical_path: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    root = _root(actor, settings)
    requested = PurePosixPath(logical_path)
    if requested.is_absolute() or ".." in requested.parts or "\\" in logical_path:
        raise HTTPException(404, "Research page not found")
    # Only the exact files in this tenant's imported edition may be served.
    catalog = _catalog(root)
    if logical_path not in catalog.get("files", {}):
        raise HTTPException(404, "Research page not found")
    path = (root / "content" / requested).resolve()
    if not path.is_relative_to(root / "content") or not path.is_file():
        raise HTTPException(404, "Research page not found")
    return FileResponse(
        path,
        media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
