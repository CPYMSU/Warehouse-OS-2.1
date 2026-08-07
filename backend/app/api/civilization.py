"""Authenticated API for Civilization content, CLI and fixed-template releases."""

from __future__ import annotations

import hashlib
import html
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, HTMLResponse

from app.api.deps import ActorContext, current_actor
from app.civilization_cli import CLI_COMMANDS, KEY_ENV
from app.civilization_cli import VERSION as CIVILIZATION_CLI_VERSION
from app.core.config import Settings, get_settings
from app.services.civilization import (
    create_thought,
    configure_public_share,
    delete_thought,
    get_public_thought,
    get_thought,
    list_revisions,
    list_thoughts,
    preview_thought,
    publish_thought,
    restore_revision,
    save_draft,
    template_catalog,
    update_thought,
    upsert_lens,
)
from app.services.runtime_api_keys import (
    RuntimeApiKeyError,
    issue_civilization_api_key,
    list_runtime_api_keys,
    revoke_runtime_api_key,
)

router = APIRouter(tags=["civilization"])


def _cli_path() -> Path:
    return Path(__file__).resolve().parents[1] / "civilization_cli.py"


def _public_page_path() -> Path:
    return Path(__file__).resolve().parents[3] / "frontend" / "v2" / "civilization-public.html"


def _key_error(exc: RuntimeApiKeyError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/api/civilization/templates")
def civilization_templates(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return template_catalog(actor)


@router.get("/api/public/civilization/{share_key}")
def civilization_public_thought(
    share_key: str,
    response: Response,
) -> dict[str, object]:
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return get_public_thought(share_key)


@router.get("/civilization/p/{share_key}", include_in_schema=False)
def civilization_public_page(share_key: str) -> HTMLResponse:
    public_post = get_public_thought(share_key)
    content = public_post.get("content")
    locales = content.get("locales") if isinstance(content, dict) else None
    localized = None
    if isinstance(locales, dict):
        localized = locales.get("zh") or locales.get("en")
    localized = localized if isinstance(localized, dict) else {}
    title = str(localized.get("title") or "Bonfire Civilization")
    description = str(localized.get("short") or localized.get("quote") or title)
    markup = _public_page_path().read_text(encoding="utf-8")
    markup = (
        markup.replace("__PAGE_TITLE__", html.escape(title, quote=True))
        .replace("__PAGE_DESCRIPTION__", html.escape(description[:300], quote=True))
        .replace("__SHARE_KEY__", html.escape(str(public_post["share_key"]), quote=True))
    )
    return HTMLResponse(
        content=markup,
        headers={"Cache-Control": "public, max-age=60, stale-while-revalidate=300"},
    )


@router.get("/api/civilization/cli/manifest")
def civilization_cli_manifest(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    path = _cli_path()
    return {
        "source": "civilization_cli_contract",
        "name": "bonfire-civilization",
        "version": CIVILIZATION_CLI_VERSION,
        "download_path": "/api/civilization/cli/download",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "credential_environment": KEY_ENV,
        "credential_scope": "civilization",
        "tenant": actor.tenant_slug,
        "template_key": "swiss_b_longform_v1",
        "commands": list(CLI_COMMANDS),
        "install": (
            'curl --fail-with-body -H "Authorization: Bearer '
            '$WAREHOUSE_CIVILIZATION_KEY" '
            "https://bonfirework.org/api/civilization/cli/download "
            "-o bonfire-civilization && chmod 700 bonfire-civilization"
        ),
    }


@router.get("/api/civilization/cli/download", response_class=FileResponse)
def civilization_cli_download(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> FileResponse:
    del actor
    path = _cli_path()
    return FileResponse(
        path=path,
        filename="bonfire-civilization",
        media_type="text/x-python; charset=utf-8",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-SHA256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    )


@router.post("/api/civilization/api-keys")
def civilization_api_key_create(
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    try:
        return issue_civilization_api_key(actor, settings, payload)
    except RuntimeApiKeyError as exc:
        raise _key_error(exc) from exc


@router.get("/api/civilization/api-keys")
def civilization_api_keys(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    try:
        return list_runtime_api_keys(actor, required_scope="civilization")
    except RuntimeApiKeyError as exc:
        raise _key_error(exc) from exc


@router.delete("/api/civilization/api-keys/{key_id}")
def civilization_api_key_delete(
    key_id: int,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    try:
        return revoke_runtime_api_key(actor, key_id, required_scope="civilization")
    except RuntimeApiKeyError as exc:
        raise _key_error(exc) from exc


@router.get("/api/civilization/thoughts")
def civilization_thoughts(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return list_thoughts(actor)


@router.post("/api/civilization/thoughts", status_code=status.HTTP_201_CREATED)
def civilization_thought_create(
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_thought(actor, payload)


@router.get("/api/civilization/thoughts/{thought_id}")
def civilization_thought_detail(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return get_thought(actor, thought_id)


@router.put("/api/civilization/thoughts/{thought_id}")
def civilization_thought_update(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return update_thought(actor, thought_id, payload)


@router.patch("/api/civilization/thoughts/{thought_id}/draft")
def civilization_thought_draft(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return save_draft(actor, thought_id, payload)


@router.get("/api/civilization/thoughts/{thought_id}/preview")
def civilization_thought_preview(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return preview_thought(actor, thought_id)


@router.post("/api/civilization/thoughts/{thought_id}/publish")
def civilization_thought_publish(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return publish_thought(actor, thought_id, payload)


@router.put("/api/civilization/thoughts/{thought_id}/share")
def civilization_thought_share(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return configure_public_share(actor, thought_id, payload)


@router.get("/api/civilization/thoughts/{thought_id}/revisions")
def civilization_thought_revisions(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return list_revisions(actor, thought_id)


@router.post("/api/civilization/thoughts/{thought_id}/revisions/{revision_no}/restore")
def civilization_thought_restore(
    thought_id: UUID,
    revision_no: int,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return restore_revision(actor, thought_id, revision_no, payload)


@router.put("/api/civilization/thoughts/{thought_id}/lenses/{lens_index}")
def civilization_thought_lens_upsert(
    thought_id: UUID,
    lens_index: int,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return upsert_lens(actor, thought_id, lens_index, payload)


@router.delete("/api/civilization/thoughts/{thought_id}")
def civilization_thought_delete(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return delete_thought(actor, thought_id)
