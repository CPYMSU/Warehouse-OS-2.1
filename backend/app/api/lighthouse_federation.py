"""Browser and device transports for Warehouse × Lighthouse federation v1."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.lighthouse_federation import (
    LighthouseFederationError,
    authenticate_device_token,
    close_device_connection,
    create_pairing_challenge,
    create_remote_run,
    enqueue_run_control,
    enroll_device,
    get_run,
    handle_device_message,
    list_devices,
    list_run_events,
    mark_outbox_delivery,
    open_device_connection,
    pending_outbox,
    revoke_device,
)
from app.services.lighthouse_protocol import make_envelope

router = APIRouter(tags=["lighthouse-federation"])


class PairingChallengeRequest(BaseModel):
    label: str = Field(default="My computer", min_length=1, max_length=120)


class DeviceEnrollmentRequest(BaseModel):
    pairing_code: str = Field(min_length=40, max_length=256)
    instance_id: UUID
    label: str | None = Field(default=None, min_length=1, max_length=120)
    public_key: str | None = Field(default=None, max_length=4096)


class RemoteRunRequest(BaseModel):
    device_id: UUID
    goal: str = Field(min_length=1, max_length=16_384)
    conversation_ref: str | None = Field(default=None, max_length=128)
    workspace_ref: str | None = Field(default=None, max_length=256)
    read_only: bool = True


class RunInputRequest(BaseModel):
    text: str = Field(min_length=1, max_length=16_384)


class RunCancelRequest(BaseModel):
    reason: str = Field(default="Cancelled by user", max_length=500)


@dataclass
class _LiveConnection:
    websocket: WebSocket
    send_lock: asyncio.Lock


class DeviceConnectionRegistry:
    """Process-local live sockets; PostgreSQL outbox remains the durable authority."""

    def __init__(self) -> None:
        self._connections: dict[UUID, _LiveConnection] = {}

    async def register(self, device_id: UUID, websocket: WebSocket) -> None:
        previous = self._connections.get(device_id)
        self._connections[device_id] = _LiveConnection(websocket, asyncio.Lock())
        if previous is not None and previous.websocket is not websocket:
            try:
                await previous.websocket.close(code=4001, reason="Replaced by a new connection")
            except RuntimeError:
                pass

    def unregister(self, device_id: UUID, websocket: WebSocket) -> None:
        current = self._connections.get(device_id)
        if current is not None and current.websocket is websocket:
            self._connections.pop(device_id, None)

    def is_online(self, device_id: UUID) -> bool:
        return device_id in self._connections

    async def send(self, device_id: UUID, envelope: dict[str, object]) -> bool:
        connection = self._connections.get(device_id)
        if connection is None:
            return False
        try:
            async with connection.send_lock:
                await connection.websocket.send_json(envelope)
            return True
        except (RuntimeError, WebSocketDisconnect):
            self.unregister(device_id, connection.websocket)
            return False

    async def close(self, device_id: UUID) -> None:
        connection = self._connections.pop(device_id, None)
        if connection is not None:
            try:
                await connection.websocket.close(code=4003, reason="Device revoked")
            except RuntimeError:
                pass


device_connections = DeviceConnectionRegistry()


def _raise_http(exc: LighthouseFederationError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post("/api/lighthouse/pairing-challenges", status_code=201)
def pairing_challenge_create(
    body: PairingChallengeRequest,
    response: Response,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _no_store(response)
    try:
        return create_pairing_challenge(actor, settings, label=body.label)
    except LighthouseFederationError as exc:
        _raise_http(exc)


@router.post("/api/lighthouse/device/v1/enroll", status_code=201)
def device_enroll(
    body: DeviceEnrollmentRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _no_store(response)
    try:
        return enroll_device(
            settings,
            pairing_code=body.pairing_code,
            instance_id=body.instance_id,
            label=body.label,
            public_key=body.public_key,
        )
    except LighthouseFederationError as exc:
        _raise_http(exc)


@router.get("/api/lighthouse/devices")
def devices_list(
    response: Response,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    try:
        devices = list_devices(actor)
    except LighthouseFederationError as exc:
        _raise_http(exc)
    for device in devices:
        device["online"] = device_connections.is_online(UUID(str(device["id"])))
    return {"ok": True, "devices": devices, "count": len(devices)}


@router.delete("/api/lighthouse/devices/{device_id}")
async def device_revoke(
    device_id: UUID,
    response: Response,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    try:
        result = revoke_device(actor, device_id)
    except LighthouseFederationError as exc:
        _raise_http(exc)
    await device_connections.close(device_id)
    return result


async def _deliver(
    *,
    tenant_id: UUID,
    device_id: UUID,
    message_id: UUID,
    envelope: dict[str, object],
) -> bool:
    delivered = await device_connections.send(device_id, envelope)
    mark_outbox_delivery(
        tenant_id,
        message_id,
        delivered=False,
        error=None if delivered else "device offline",
        device_id=device_id,
    )
    return delivered


@router.post("/api/lighthouse/runs", status_code=202)
async def run_create(
    body: RemoteRunRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    try:
        run, envelope, message_id = create_remote_run(
            actor,
            device_id=body.device_id,
            goal=body.goal,
            conversation_ref=body.conversation_ref,
            workspace_ref=body.workspace_ref,
            client_request_id=idempotency_key,
            read_only=body.read_only,
        )
    except LighthouseFederationError as exc:
        _raise_http(exc)
    sent = False
    if envelope:
        sent = await _deliver(
            tenant_id=actor.tenant_id,
            device_id=body.device_id,
            message_id=message_id,
            envelope=envelope,
        )
    return {
        "ok": True,
        "run": run,
        "delivery_state": "sent_unacknowledged" if sent else "queued",
    }


@router.get("/api/lighthouse/runs/{run_id}")
def run_get(
    run_id: UUID,
    response: Response,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    try:
        return {"ok": True, "run": get_run(actor, run_id)}
    except LighthouseFederationError as exc:
        _raise_http(exc)


@router.get("/api/lighthouse/runs/{run_id}/events")
def run_events_list(
    run_id: UUID,
    response: Response,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    try:
        events = list_run_events(
            actor,
            run_id,
            after_sequence=after_sequence,
            limit=limit,
        )
    except LighthouseFederationError as exc:
        _raise_http(exc)
    return {"ok": True, "events": events, "count": len(events)}


@router.get("/api/lighthouse/runs/{run_id}/stream")
def run_events_stream(
    run_id: UUID,
    after_sequence: int = Query(default=0, ge=0),
    follow: bool = Query(default=True),
    actor: ActorContext = Depends(current_actor),
) -> StreamingResponse:
    try:
        get_run(actor, run_id)
    except LighthouseFederationError as exc:
        _raise_http(exc)

    async def event_source():
        cursor = after_sequence
        idle_ticks = 0
        while True:
            events = list_run_events(actor, run_id, after_sequence=cursor, limit=200)
            for event in events:
                cursor = int(event["sequence"])
                yield (
                    f"id: {cursor}\n"
                    f"event: {event['type']}\n"
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                )
            if not follow:
                return
            if events:
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks % 20 == 0:
                    yield ": heartbeat\n\n"
            run = get_run(actor, run_id)
            if run["status"] in {"completed", "failed", "cancelled", "rejected"} and not events:
                return
            await asyncio.sleep(1)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/api/lighthouse/runs/{run_id}/input", status_code=202)
async def run_input(
    run_id: UUID,
    body: RunInputRequest,
    response: Response,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    try:
        envelope, message_id, device_id = enqueue_run_control(
            actor,
            run_id,
            message_type="run.input",
            value=body.text,
        )
    except LighthouseFederationError as exc:
        _raise_http(exc)
    sent = await _deliver(
        tenant_id=actor.tenant_id,
        device_id=device_id,
        message_id=message_id,
        envelope=envelope,
    )
    return {
        "ok": True,
        "run_id": str(run_id),
        "delivery_state": "sent_unacknowledged" if sent else "queued",
    }


@router.post("/api/lighthouse/runs/{run_id}/cancel", status_code=202)
async def run_cancel(
    run_id: UUID,
    body: RunCancelRequest,
    response: Response,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    try:
        envelope, message_id, device_id = enqueue_run_control(
            actor,
            run_id,
            message_type="run.cancel",
            value=body.reason,
        )
    except LighthouseFederationError as exc:
        _raise_http(exc)
    sent = await _deliver(
        tenant_id=actor.tenant_id,
        device_id=device_id,
        message_id=message_id,
        envelope=envelope,
    )
    return {
        "ok": True,
        "run_id": str(run_id),
        "delivery_state": "sent_unacknowledged" if sent else "queued",
    }


@router.websocket("/api/lighthouse/device/v1/connect")
async def device_connect(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
) -> None:
    authorization = websocket.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Bearer token required")
        return
    try:
        principal = authenticate_device_token(token.strip(), settings)
    except LighthouseFederationError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid device token")
        return

    connection_id: UUID | None = None
    await websocket.accept(subprotocol=None)
    await device_connections.register(principal.device_id, websocket)
    try:
        connection_id = open_device_connection(principal)
        for envelope in pending_outbox(principal):
            delivered = await device_connections.send(principal.device_id, envelope)
            mark_outbox_delivery(
                principal.tenant_id,
                envelope["message_id"],
                delivered=False,
                error=None if delivered else "connection closed during replay",
                device_id=principal.device_id,
            )
            if not delivered:
                return
        while True:
            raw = await websocket.receive_json()
            try:
                outcome = handle_device_message(principal, raw)
                if outcome.get("acknowledgement"):
                    continue
                ack_payload = {**outcome, "accepted": True}
            except LighthouseFederationError as exc:
                ack_payload = {
                    "received_message_id": str(raw.get("message_id") or "")
                    if isinstance(raw, dict)
                    else "",
                    "accepted": False,
                    "error": str(exc),
                }
            ack = make_envelope("message.ack", ack_payload)
            if not await device_connections.send(principal.device_id, ack):
                return
    except WebSocketDisconnect:
        pass
    finally:
        device_connections.unregister(principal.device_id, websocket)
        if connection_id is not None:
            close_device_connection(principal, connection_id)
