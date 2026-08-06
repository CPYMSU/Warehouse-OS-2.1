"""Authenticated research project, preview and revision API."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.research_cli import CLI_COMMANDS, KEY_ENV
from app.research_cli import VERSION as RESEARCH_CLI_VERSION
from app.services.object_storage import LocalContentAddressedObjectStore
from app.services.research_execution import (
    artifact_descriptor,
    cancel_execution,
    create_execution,
    execution_detail,
    execution_runtimes,
    list_executions,
    promote_artifact,
    retry_execution,
)
from app.services.research_refinement import (
    publish_refinement,
    refinement_media,
    refinement_workspace,
    save_refinement_draft,
)
from app.services.research_review import (
    add_annotation_message,
    ask_document,
    create_annotation,
    distill_document_index,
    document_workspace,
    queue_document_index,
    set_annotation_status,
)
from app.services.research_vault import (
    add_file_version,
    content_descriptor,
    create_project,
    diff_file,
    file_versions,
    list_projects,
    preview_file,
    project_commits,
    project_detail,
    require_research_write,
    research_formats,
    upload_contract,
)
from app.services.research_workflow import (
    create_claim,
    create_protocol,
    create_release,
    create_run,
    link_claim_evidence,
    release_detail,
    run_reproduction_check,
    save_dmp,
    submit_review,
    update_run,
    workflow_detail,
)

router = APIRouter(tags=["research-vault"])


def _research_cli_path() -> Path:
    return Path(__file__).resolve().parents[1] / "research_cli.py"


@router.get("/api/research/cli/manifest")
def research_cli_manifest(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    """Describe the downloadable, key-authenticated headless client."""
    path = _research_cli_path()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "source": "research_cli_contract",
        "name": "bonfire-research",
        "version": RESEARCH_CLI_VERSION,
        "download_path": "/api/research/cli/download",
        "sha256": digest,
        "credential_environment": KEY_ENV,
        "credential_scope": "research",
        "tenant": actor.tenant_slug,
        "commands": list(CLI_COMMANDS),
        "install": (
            "curl --fail-with-body -H \"Authorization: Bearer "
            "$WAREHOUSE_RESEARCH_KEY\" "
            "https://bonfirework.org/api/research/cli/download "
            "-o bonfire-research && chmod 700 bonfire-research"
        ),
    }


@router.get("/api/research/cli/download", response_class=FileResponse)
def research_cli_download(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> FileResponse:
    """Download the dependency-free CLI after a live research authorization check."""
    del actor
    path = _research_cli_path()
    return FileResponse(
        path=path,
        filename="bonfire-research",
        media_type="text/x-python; charset=utf-8",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-SHA256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    )


@router.get("/api/research/execution-runtimes")
def research_execution_runtimes(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return execution_runtimes(actor)


@router.get("/api/research/projects")
def research_projects(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return list_projects(actor)


@router.post("/api/research/projects", status_code=status.HTTP_201_CREATED)
def research_project_create(
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_project(actor, payload, settings)


@router.get("/api/research/formats")
def research_format_capabilities(
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return research_formats(actor, settings)


@router.get("/api/research/projects/{project_ref}")
def research_project_show(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return project_detail(actor, project_ref)


@router.get("/api/research/projects/{project_ref}/upload-contract")
def research_project_upload_contract(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return upload_contract(actor, project_ref, settings)


@router.get("/api/research/projects/{project_ref}/commits")
def research_project_commits(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    limit: int = Query(default=80, ge=1, le=200),
) -> dict[str, object]:
    return project_commits(actor, project_ref, limit)


@router.post(
    "/api/research/projects/{project_ref}/files",
    status_code=status.HTTP_201_CREATED,
)
def research_file_upload(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: UploadFile = File(...),
    logical_path: str | None = Form(default=None),
    commit_message: str | None = Form(default=None),
    expected_sha256: str | None = Form(default=None),
    background_tasks: BackgroundTasks = None,
) -> dict[str, object]:
    require_research_write(actor)
    store = LocalContentAddressedObjectStore(settings.asset_storage_root)
    stored = store.put_stream(
        tenant_id=actor.tenant_id,
        stream=file.file,
        max_bytes=settings.research_max_upload_bytes,
        expected_sha256=expected_sha256,
    )
    result = add_file_version(
        actor,
        project_ref,
        stored=stored,
        store=store,
        original_filename=file.filename or "research-file",
        content_type=file.content_type,
        logical_path=logical_path,
        commit_message=commit_message,
        settings=settings,
    )
    version_id = (result.get("version") or {}).get("id")
    if version_id:
        queue_document_index(actor, version_id)
        if background_tasks is not None:
            background_tasks.add_task(distill_document_index, actor, version_id, settings)
    return result


@router.get("/api/research/projects/{project_ref}/files/{file_ref}/versions")
def research_file_versions(
    project_ref: str,
    file_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return file_versions(actor, project_ref, file_ref)


@router.get("/api/research/projects/{project_ref}/files/{file_ref}/preview")
def research_file_preview(
    project_ref: str,
    file_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    version: int | None = Query(default=None, ge=1),
) -> dict[str, object]:
    return preview_file(actor, project_ref, file_ref, version, settings)


@router.get("/api/research/projects/{project_ref}/files/{file_ref}/review")
def research_file_review_workspace(
    project_ref: str,
    file_ref: str,
    background_tasks: BackgroundTasks,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    version: int | None = Query(default=None, ge=1),
) -> dict[str, object]:
    result = document_workspace(actor, project_ref, file_ref, version, settings)
    index = result.get("index") if isinstance(result.get("index"), dict) else {}
    if index.get("distillation_status") in {"queued", "failed"}:
        background_tasks.add_task(
            distill_document_index,
            actor,
            (result.get("version") or {}).get("id"),
            settings,
        )
    return result


@router.post("/api/research/projects/{project_ref}/files/{file_ref}/refinement")
def research_manuscript_refinement_workspace(
    project_ref: str,
    file_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    """Start or resume one browser-local manuscript draft."""

    return refinement_workspace(actor, project_ref, file_ref, settings)


@router.put("/api/research/projects/{project_ref}/files/{file_ref}/refinement")
def research_manuscript_refinement_save(
    project_ref: str,
    file_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(...),
) -> dict[str, object]:
    """Optimistically synchronize a recoverable structured manuscript draft."""

    return save_refinement_draft(actor, project_ref, file_ref, payload)


@router.post("/api/research/projects/{project_ref}/files/{file_ref}/refinement/submit")
def research_manuscript_refinement_submit(
    project_ref: str,
    file_ref: str,
    background_tasks: BackgroundTasks,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(...),
) -> dict[str, object]:
    """Assemble the content draft into one immutable DOCX and Git version."""

    result = publish_refinement(actor, project_ref, file_ref, payload, settings)
    version_id = (result.get("version") or {}).get("id")
    if version_id:
        background_tasks.add_task(distill_document_index, actor, version_id, settings)
    return result


@router.get(
    "/api/research/projects/{project_ref}/files/{file_ref}/refinement/media/{relationship_id}"
)
def research_manuscript_refinement_media(
    project_ref: str,
    file_ref: str,
    relationship_id: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    version: int | None = Query(default=None, ge=1),
) -> Response:
    """Serve one validated source figure without exposing object-storage keys."""

    content, content_type = refinement_media(
        actor, project_ref, file_ref, relationship_id, version, settings
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post(
    "/api/research/projects/{project_ref}/files/{file_ref}/annotations",
    status_code=status.HTTP_201_CREATED,
)
def research_file_annotation_create(
    project_ref: str,
    file_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_annotation(actor, project_ref, file_ref, payload, settings)


@router.post(
    "/api/research/projects/{project_ref}/files/{file_ref}/questions",
    status_code=status.HTTP_201_CREATED,
)
def research_file_question_create(
    project_ref: str,
    file_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return ask_document(actor, project_ref, file_ref, payload, settings)


@router.post(
    "/api/research/document-annotations/{annotation_id}/messages",
    status_code=status.HTTP_201_CREATED,
)
def research_document_annotation_message(
    annotation_id: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return add_annotation_message(actor, annotation_id, payload)


@router.post("/api/research/document-annotations/{annotation_id}/status")
def research_document_annotation_status(
    annotation_id: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return set_annotation_status(actor, annotation_id, bool(payload.get("resolved", True)))


@router.get("/api/research/projects/{project_ref}/files/{file_ref}/diff")
def research_file_diff(
    project_ref: str,
    file_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    from_version: int | None = Query(default=None, ge=1),
    to_version: int | None = Query(default=None, ge=1),
) -> dict[str, object]:
    return diff_file(
        actor,
        project_ref,
        file_ref,
        from_version,
        to_version,
        settings,
    )


@router.get("/api/research/projects/{project_ref}/files/{file_ref}/content")
def research_file_content(
    project_ref: str,
    file_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    version: int | None = Query(default=None, ge=1),
) -> FileResponse:
    descriptor = content_descriptor(actor, project_ref, file_ref, version, settings)
    filename = str(descriptor["filename"])
    return FileResponse(
        path=descriptor["path"],
        media_type=str(descriptor["content_type"]),
        headers={
            "Content-Disposition": (f"inline; filename*=UTF-8''{quote(filename, safe='')}"),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "X-Content-SHA256": str(descriptor["content_sha256"]),
        },
    )


@router.get("/api/research/projects/{project_ref}/workflow")
def research_workflow_show(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return workflow_detail(actor, project_ref)


@router.get("/api/research/projects/{project_ref}/dmp")
def research_dmp_show(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    detail = workflow_detail(actor, project_ref)
    return {
        "source": detail["source"],
        "project": detail["project"],
        "dmp": detail["dmp"],
        "history": detail["dmp_history"],
    }


@router.put("/api/research/projects/{project_ref}/dmp")
def research_dmp_save(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return save_dmp(actor, project_ref, payload)


@router.get("/api/research/projects/{project_ref}/protocols")
def research_protocols(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    detail = workflow_detail(actor, project_ref)
    return {
        "source": detail["source"],
        "project": detail["project"],
        "protocols": detail["protocols"],
    }


@router.post(
    "/api/research/projects/{project_ref}/protocols",
    status_code=status.HTTP_201_CREATED,
)
def research_protocol_create(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_protocol(actor, project_ref, payload)


@router.get("/api/research/projects/{project_ref}/runs")
def research_runs(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    detail = workflow_detail(actor, project_ref)
    return {
        "source": detail["source"],
        "project": detail["project"],
        "runs": detail["runs"],
    }


@router.post(
    "/api/research/projects/{project_ref}/runs",
    status_code=status.HTTP_201_CREATED,
)
def research_run_create(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_run(actor, project_ref, payload)


@router.patch("/api/research/projects/{project_ref}/runs/{run_ref}")
def research_run_update(
    project_ref: str,
    run_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return update_run(actor, project_ref, run_ref, payload)


@router.get("/api/research/projects/{project_ref}/claims")
def research_claims(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    detail = workflow_detail(actor, project_ref)
    return {
        "source": detail["source"],
        "project": detail["project"],
        "claims": detail["claims"],
    }


@router.post(
    "/api/research/projects/{project_ref}/claims",
    status_code=status.HTTP_201_CREATED,
)
def research_claim_create(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_claim(actor, project_ref, payload)


@router.post(
    "/api/research/projects/{project_ref}/claims/{claim_ref}/evidence",
    status_code=status.HTTP_201_CREATED,
)
def research_claim_evidence_link(
    project_ref: str,
    claim_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return link_claim_evidence(actor, project_ref, claim_ref, payload)


@router.get("/api/research/projects/{project_ref}/reviews")
def research_reviews(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    detail = workflow_detail(actor, project_ref)
    return {
        "source": detail["source"],
        "project": detail["project"],
        "reviews": detail["reviews"],
    }


@router.post(
    "/api/research/projects/{project_ref}/reviews",
    status_code=status.HTTP_201_CREATED,
)
def research_review_submit(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return submit_review(actor, project_ref, payload)


@router.post(
    "/api/research/projects/{project_ref}/reproducibility-checks",
    status_code=status.HTTP_201_CREATED,
)
def research_reproducibility_check(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return run_reproduction_check(actor, project_ref)


@router.get("/api/research/projects/{project_ref}/executions")
def research_execution_list(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return list_executions(actor, project_ref)


@router.post(
    "/api/research/projects/{project_ref}/executions",
    status_code=status.HTTP_202_ACCEPTED,
)
def research_execution_submit(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_execution(actor, project_ref, payload, settings)


@router.get("/api/research/projects/{project_ref}/executions/{execution_ref}")
def research_execution_show(
    project_ref: str,
    execution_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return execution_detail(actor, project_ref, execution_ref)


@router.post("/api/research/projects/{project_ref}/executions/{execution_ref}/cancel")
def research_execution_cancel(
    project_ref: str,
    execution_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return cancel_execution(actor, project_ref, execution_ref)


@router.post(
    "/api/research/projects/{project_ref}/executions/{execution_ref}/retry",
    status_code=status.HTTP_202_ACCEPTED,
)
def research_execution_retry(
    project_ref: str,
    execution_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return retry_execution(actor, project_ref, execution_ref, settings)


@router.get(
    "/api/research/projects/{project_ref}/executions/{execution_ref}/artifacts/{artifact_ref}/content"
)
def research_execution_artifact_content(
    project_ref: str,
    execution_ref: str,
    artifact_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    descriptor = artifact_descriptor(
        actor, project_ref, execution_ref, artifact_ref, settings
    )
    filename = str(descriptor["relative_path"]).rsplit("/", 1)[-1]
    return FileResponse(
        path=descriptor["path"],
        media_type=str(descriptor["content_type"]),
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename, safe='')}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "X-Content-SHA256": str(descriptor["content_sha256"]),
        },
    )


@router.post(
    "/api/research/projects/{project_ref}/executions/{execution_ref}/artifacts/{artifact_ref}/promote",
    status_code=status.HTTP_201_CREATED,
)
def research_execution_artifact_promote(
    project_ref: str,
    execution_ref: str,
    artifact_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return promote_artifact(
        actor, project_ref, execution_ref, artifact_ref, payload, settings
    )


@router.get("/api/research/projects/{project_ref}/releases")
def research_releases(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    detail = workflow_detail(actor, project_ref)
    return {
        "source": detail["source"],
        "project": detail["project"],
        "releases": detail["releases"],
    }


@router.post(
    "/api/research/projects/{project_ref}/releases",
    status_code=status.HTTP_201_CREATED,
)
def research_release_create(
    project_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_release(actor, project_ref, payload)


@router.get("/api/research/projects/{project_ref}/releases/{release_ref}")
def research_release_show(
    project_ref: str,
    release_ref: str,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return release_detail(actor, project_ref, release_ref)
