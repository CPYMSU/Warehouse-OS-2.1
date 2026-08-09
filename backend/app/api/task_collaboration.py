"""Native PostgreSQL task collaboration API."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.task_collaboration import (
    decide_request,
    discover_spaces,
    get_space,
    invite_member,
    leave_space,
    list_messages,
    mark_read,
    open_space,
    request_or_join,
    respond_invitation,
    send_message,
    transfer_ownership,
)
from app.services.task_collaboration_documents import (
    IMAGE_ASSET_MIME_TYPES,
    MAX_IMAGE_ASSET_BYTES,
    MAX_IMAGE_ASSET_DIMENSION,
    append_update,
    export_document,
    get_document,
    image_descriptor,
    register_image,
)
from app.services.task_collaboration_annotations import (
    accept_review_change,
    add_annotation_message,
    create_annotation,
    create_review_change,
    list_annotations,
    reject_review_change,
    update_annotation_status,
)
from app.services.task_collaboration_realtime import (
    authorize_stream,
    event_stream,
    get_position,
    update_presence,
)

router = APIRouter(tags=["task-collaboration"])


@router.get("/api/task-collaboration/discover")
def collaboration_discover(
    limit: int = Query(default=30, ge=1, le=100),
    cursor: int | None = Query(default=None, ge=0),
    q: str = Query(default="", max_length=120),
    discoverability: str | None = Query(default=None),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return discover_spaces(
        actor,
        {
            "limit": limit,
            "cursor": cursor,
            "q": q,
            "discoverability": discoverability,
        },
    )


@router.get("/api/tasks/{task_id}/collaboration")
def collaboration_get(
    task_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return get_space(actor, task_id)


@router.post("/api/tasks/{task_id}/collaboration/open", status_code=status.HTTP_201_CREATED)
def collaboration_open(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return open_space(actor, task_id, payload)


@router.post("/api/tasks/{task_id}/collaboration/join")
def collaboration_join(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return request_or_join(actor, task_id, payload)


@router.post("/api/tasks/{task_id}/collaboration/leave")
def collaboration_leave(
    task_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return leave_space(actor, task_id)


@router.post("/api/tasks/{task_id}/collaboration/invite", status_code=status.HTTP_201_CREATED)
def collaboration_invite(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return invite_member(actor, task_id, payload)


@router.post("/api/tasks/{task_id}/collaboration/requests/{request_id}/decision")
def collaboration_request_decision(
    task_id: str,
    request_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return decide_request(actor, task_id, request_id, payload)


@router.post("/api/tasks/{task_id}/collaboration/invitations/{invitation_id}/respond")
def collaboration_invitation_response(
    task_id: str,
    invitation_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return respond_invitation(actor, task_id, invitation_id, payload)


@router.post("/api/tasks/{task_id}/collaboration/owner/transfer")
def collaboration_owner_transfer(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return transfer_ownership(actor, task_id, payload)


@router.get("/api/tasks/{task_id}/collaboration/messages")
def collaboration_messages(
    task_id: str,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return list_messages(actor, task_id, after_id, limit)


@router.post("/api/tasks/{task_id}/collaboration/messages", status_code=status.HTTP_201_CREATED)
def collaboration_message_send(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return send_message(actor, task_id, payload)


@router.post("/api/tasks/{task_id}/collaboration/read")
def collaboration_message_read(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return mark_read(actor, task_id, payload)


@router.post("/api/tasks/{task_id}/collaboration/presence")
def collaboration_presence_update(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return update_presence(actor, task_id, payload)


@router.get("/api/tasks/{task_id}/collaboration/position")
def collaboration_position_get(
    task_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return get_position(actor, task_id)


@router.get("/api/tasks/{task_id}/collaboration/annotations")
def collaboration_annotations(
    task_id: str,
    annotation_status: str = Query(default="all", alias="status"),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return list_annotations(actor, task_id, annotation_status)


@router.post(
    "/api/tasks/{task_id}/collaboration/annotations",
    status_code=status.HTTP_201_CREATED,
)
def collaboration_annotation_create(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return create_annotation(actor, task_id, payload)


@router.post(
    "/api/tasks/{task_id}/collaboration/review-changes",
    status_code=status.HTTP_201_CREATED,
)
def collaboration_review_change_create(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return create_review_change(actor, task_id, payload)


@router.post(
    "/api/tasks/{task_id}/collaboration/review-changes/{annotation_id}/accept"
)
def collaboration_review_change_accept(
    task_id: str,
    annotation_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return accept_review_change(actor, task_id, annotation_id)


@router.post(
    "/api/tasks/{task_id}/collaboration/review-changes/{annotation_id}/reject"
)
def collaboration_review_change_reject(
    task_id: str,
    annotation_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return reject_review_change(actor, task_id, annotation_id)


@router.post(
    "/api/tasks/{task_id}/collaboration/annotations/{annotation_id}/messages",
    status_code=status.HTTP_201_CREATED,
)
def collaboration_annotation_message(
    task_id: str,
    annotation_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return add_annotation_message(actor, task_id, annotation_id, payload)


@router.post("/api/tasks/{task_id}/collaboration/annotations/{annotation_id}/status")
def collaboration_annotation_status(
    task_id: str,
    annotation_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return update_annotation_status(actor, task_id, annotation_id, payload)


@router.get("/api/tasks/{task_id}/collaboration/events")
def collaboration_events(
    task_id: str,
    after_event_id: int = Query(default=0, ge=0),
    after_signal_id: int = Query(default=0, ge=0),
    client_id: str | None = Query(default=None, min_length=1, max_length=80),
    actor: ActorContext = Depends(current_actor),
) -> StreamingResponse:
    del after_signal_id, client_id
    authorize_stream(actor, task_id)
    return StreamingResponse(
        event_stream(actor, task_id, after_event_id),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "private, no-cache, no-store, max-age=0",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 12 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise HTTPException(status_code=422, detail="Invalid JPEG image")
    offset = 2
    frame_markers = {
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
    }
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            raise HTTPException(status_code=422, detail="Invalid JPEG image")
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0x01, *range(0xD0, 0xD9)}:
            continue
        if marker in {0xD9, 0xDA} or offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset : offset + 2], "big")
        if length < 2 or offset + length > len(data):
            raise HTTPException(status_code=422, detail="Invalid JPEG image")
        if marker in frame_markers:
            if length < 7:
                raise HTTPException(status_code=422, detail="Invalid JPEG image")
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            return width, height
        offset += length
    raise HTTPException(status_code=422, detail="JPEG image has no supported frame")


def _webp_dimensions(data: bytes) -> tuple[int, int]:
    if (
        len(data) < 30
        or data[:4] != b"RIFF"
        or data[8:12] != b"WEBP"
        or int.from_bytes(data[4:8], "little") + 8 != len(data)
    ):
        raise HTTPException(status_code=422, detail="Invalid WebP image")
    offset = 12
    while offset + 8 <= len(data):
        kind = data[offset : offset + 4]
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        start = offset + 8
        end = start + size
        if end > len(data):
            raise HTTPException(status_code=422, detail="Invalid WebP image")
        payload = data[start:end]
        if kind == b"VP8X" and len(payload) >= 10:
            return (
                int.from_bytes(payload[4:7], "little") + 1,
                int.from_bytes(payload[7:10], "little") + 1,
            )
        if kind == b"VP8L" and len(payload) >= 5 and payload[0] == 0x2F:
            bits = int.from_bytes(payload[1:5], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if kind == b"VP8 " and len(payload) >= 10 and payload[3:6] == b"\x9d\x01\x2a":
            return (
                int.from_bytes(payload[6:8], "little") & 0x3FFF,
                int.from_bytes(payload[8:10], "little") & 0x3FFF,
            )
        offset = end + (size % 2)
    raise HTTPException(status_code=422, detail="WebP image has no supported frame")


def _image_dimensions(data: bytes, mime_type: str) -> tuple[int, int]:
    if mime_type == "image/png":
        if (
            len(data) < 33
            or data[:8] != b"\x89PNG\r\n\x1a\n"
            or data[12:16] != b"IHDR"
        ):
            raise HTTPException(status_code=422, detail="Invalid PNG image")
        dimensions = (
            int.from_bytes(data[16:20], "big"),
            int.from_bytes(data[20:24], "big"),
        )
    elif mime_type == "image/jpeg":
        dimensions = _jpeg_dimensions(data)
    elif mime_type == "image/webp":
        dimensions = _webp_dimensions(data)
    else:
        raise HTTPException(status_code=415, detail="Only PNG, JPEG and WebP are supported")
    width, height = dimensions
    if not 1 <= width <= MAX_IMAGE_ASSET_DIMENSION or not 1 <= height <= MAX_IMAGE_ASSET_DIMENSION:
        raise HTTPException(
            status_code=413,
            detail=f"Image dimensions are limited to {MAX_IMAGE_ASSET_DIMENSION} pixels",
        )
    return dimensions


@router.get("/api/tasks/{task_id}/collaboration/document")
def collaboration_document_get(
    task_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return get_document(actor, task_id)


@router.post("/api/tasks/{task_id}/collaboration/document/updates")
def collaboration_document_update(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return append_update(actor, task_id, payload)


@router.post(
    "/api/tasks/{task_id}/collaboration/document/images",
    status_code=status.HTTP_201_CREATED,
)
async def collaboration_document_image_upload(
    task_id: str,
    image: UploadFile = File(...),
    alt_text: str = Form(default="", max_length=160),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    mime_type = str(image.content_type or "").split(";", 1)[0].strip().lower()
    if mime_type not in IMAGE_ASSET_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Only PNG, JPEG and WebP are supported")
    data = await image.read(MAX_IMAGE_ASSET_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail="Image cannot be empty")
    if len(data) > MAX_IMAGE_ASSET_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 2 MB")
    width, height = _image_dimensions(data, mime_type)
    return register_image(
        actor,
        task_id,
        data=data,
        file_name=image.filename or "image",
        alt_text=alt_text,
        mime_type=mime_type,
        width=width,
        height=height,
        settings=settings,
    )


@router.get("/api/tasks/{task_id}/collaboration/document/images/{asset_key}")
def collaboration_document_image_get(
    task_id: str,
    asset_key: str,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    descriptor = image_descriptor(actor, task_id, asset_key, settings)
    return FileResponse(
        descriptor["path"],
        media_type=str(descriptor["mime_type"]),
        filename=str(descriptor["filename"]),
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "ETag": f'"sha256-{descriptor["sha256"]}"',
        },
    )


@router.get("/api/tasks/{task_id}/collaboration/document/export")
def collaboration_document_export(
    task_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return export_document(actor, task_id)
