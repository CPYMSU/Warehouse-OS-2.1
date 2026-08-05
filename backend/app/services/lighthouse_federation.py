"""Durable, tenant-scoped relay for user-owned Lighthouse instances."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import text

from app.api.deps import ActorContext
from app.core.config import Settings
from app.db.session import system_session, tenant_session
from app.services.lighthouse_protocol import PROTOCOL, make_envelope, parse_device_message

PAIRING_PREFIX = "whp"
DEVICE_PREFIX = "whd"
PAIRING_TTL_MINUTES = 10
_TENANT_PATTERN = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_PAIRING_RE = re.compile(
    rf"^{PAIRING_PREFIX}_({_TENANT_PATTERN})_([a-f0-9]{{12}})_([A-Za-z0-9_-]{{24,}})$"
)
_DEVICE_RE = re.compile(
    rf"^{DEVICE_PREFIX}_({_TENANT_PATTERN})_([a-f0-9]{{12}})_([A-Za-z0-9_-]{{32,}})$"
)


class LighthouseFederationError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class DevicePrincipal:
    tenant_id: UUID
    tenant_slug: str
    device_id: UUID
    owner_user_id: UUID
    instance_id: UUID


def _digest(kind: str, plain: str, settings: Settings) -> str:
    material = f"warehouse-lighthouse:{kind}:v1:{plain}".encode()
    return hmac.new(
        settings.integration_secret.encode(), material, hashlib.sha256
    ).hexdigest()


def _parse_uuid(value: object, field: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise LighthouseFederationError(f"{field} must be a UUID") from exc


def _visible_text(value: object, field: str, *, maximum: int) -> str:
    result = str(value or "").strip()
    if not result or len(result) > maximum or any(not char.isprintable() for char in result):
        raise LighthouseFederationError(
            f"{field} must contain 1 to {maximum} visible characters"
        )
    return result


def _bounded_text(value: object, field: str, *, maximum: int) -> str:
    result = str(value or "").strip()
    if not result or len(result) > maximum or "\x00" in result:
        raise LighthouseFederationError(f"{field} must contain 1 to {maximum} characters")
    return result


def _iso(value: object) -> object:
    return value.isoformat() if isinstance(value, datetime) else value


def _device_public(item: dict[str, object], *, online: bool = False) -> dict[str, object]:
    return {
        "id": str(item["id"]),
        "instance_id": str(item["instance_id"]),
        "label": item["label"],
        "status": item["status"],
        "online": online,
        "protocol_version": item["protocol_version"],
        "capabilities": list(item.get("capabilities") or []),
        "metadata": dict(item.get("metadata") or {}),
        "connected_at": _iso(item.get("connected_at")),
        "last_seen_at": _iso(item.get("last_seen_at")),
        "created_at": _iso(item.get("created_at")),
    }


def _run_public(item: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(item["id"]),
        "device_id": str(item["device_id"]),
        "conversation_ref": item.get("conversation_ref"),
        "workspace_ref": item.get("workspace_ref"),
        "goal": item["goal"],
        "policy": dict(item.get("policy") or {}),
        "status": item["status"],
        "local_run_ref": item.get("local_run_ref"),
        "result": item.get("result"),
        "error": item.get("error"),
        "event_cursor": int(item.get("event_cursor") or 0),
        "created_at": _iso(item.get("created_at")),
        "updated_at": _iso(item.get("updated_at")),
        "completed_at": _iso(item.get("completed_at")),
    }


def create_pairing_challenge(
    actor: ActorContext,
    settings: Settings,
    *,
    label: object,
) -> dict[str, object]:
    if actor.auth_kind != "session":
        raise LighthouseFederationError("Pairing requires an interactive session", 403)
    if "ai.use" not in actor.permissions:
        raise LighthouseFederationError("Current account cannot pair Lighthouse", 403)
    requested_label = _visible_text(label or "My computer", "label", maximum=120)
    challenge_id = uuid4()
    public_id = secrets.token_hex(6)
    secret = secrets.token_urlsafe(24)
    plain = f"{PAIRING_PREFIX}_{actor.tenant_slug}_{public_id}_{secret}"
    expires_at = datetime.now(UTC) + timedelta(minutes=PAIRING_TTL_MINUTES)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO lighthouse.pairing_challenges(
                  id, tenant_id, owner_user_id, public_id, code_hash,
                  requested_label, expires_at
                ) VALUES (
                  :id, :tenant_id, :owner_user_id, :public_id, :code_hash,
                  :requested_label, :expires_at
                )
                """
            ),
            {
                "id": challenge_id,
                "tenant_id": actor.tenant_id,
                "owner_user_id": actor.user_id,
                "public_id": public_id,
                "code_hash": _digest("pairing-code", plain, settings),
                "requested_label": requested_label,
                "expires_at": expires_at,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (
                  :tenant_id, :actor_user_id, 'lighthouse.pairing.created',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": json.dumps(
                    {"challenge_id": str(challenge_id), "label": requested_label}
                ),
            },
        )
    return {
        "ok": True,
        "challenge_id": str(challenge_id),
        "pairing_code": plain,
        "expires_at": expires_at.isoformat(),
        "note": "This one-time pairing code is shown once and expires in ten minutes.",
    }


def _tenant_for_slug(slug: str) -> UUID | None:
    with system_session() as session:
        return session.execute(
            text("SELECT id FROM iam.tenants WHERE slug = :slug AND status = 'active'"),
            {"slug": slug},
        ).scalar_one_or_none()


def enroll_device(
    settings: Settings,
    *,
    pairing_code: object,
    instance_id: object,
    label: object = None,
    public_key: object = None,
) -> dict[str, object]:
    plain_code = str(pairing_code or "").strip()
    match = _PAIRING_RE.fullmatch(plain_code)
    if not match:
        raise LighthouseFederationError("Invalid or expired pairing code", 401)
    tenant_slug, challenge_public_id = match.group(1), match.group(2)
    tenant_id = _tenant_for_slug(tenant_slug)
    if tenant_id is None:
        raise LighthouseFederationError("Invalid or expired pairing code", 401)
    parsed_instance_id = _parse_uuid(instance_id, "instance_id")
    clean_public_key = str(public_key or "").strip() or None
    if clean_public_key is not None and len(clean_public_key) > 4096:
        raise LighthouseFederationError("public_key is too long")

    token_public_id = secrets.token_hex(6)
    token_secret = secrets.token_urlsafe(32)
    token = f"{DEVICE_PREFIX}_{tenant_slug}_{token_public_id}_{token_secret}"
    token_hint = f"{DEVICE_PREFIX}_{tenant_slug}_{token_public_id}_····{token_secret[-4:]}"
    now = datetime.now(UTC)
    with tenant_session(tenant_id) as session:
        challenge = (
            session.execute(
                text(
                    """
                    SELECT id, owner_user_id, code_hash, requested_label, expires_at, consumed_at
                    FROM lighthouse.pairing_challenges
                    WHERE public_id = :public_id
                    FOR UPDATE
                    """
                ),
                {"public_id": challenge_public_id},
            )
            .mappings()
            .one_or_none()
        )
        if (
            challenge is None
            or challenge["consumed_at"] is not None
            or challenge["expires_at"] <= now
            or not hmac.compare_digest(
                str(challenge["code_hash"]), _digest("pairing-code", plain_code, settings)
            )
        ):
            raise LighthouseFederationError("Invalid or expired pairing code", 401)
        device_label = _visible_text(
            label or challenge["requested_label"], "label", maximum=120
        )
        existing = (
            session.execute(
                text(
                    """
                    SELECT id FROM lighthouse.devices
                    WHERE owner_user_id = :owner_user_id AND instance_id = :instance_id
                    FOR UPDATE
                    """
                ),
                {
                    "owner_user_id": challenge["owner_user_id"],
                    "instance_id": parsed_instance_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        device_id = existing["id"] if existing else uuid4()
        if existing:
            session.execute(
                text(
                    """
                    UPDATE lighthouse.devices
                    SET label = :label, public_key = :public_key,
                        token_public_id = :token_public_id, token_hash = :token_hash,
                        token_hint = :token_hint, status = 'active', revoked_at = NULL
                    WHERE id = :device_id
                    """
                ),
                {
                    "device_id": device_id,
                    "label": device_label,
                    "public_key": clean_public_key,
                    "token_public_id": token_public_id,
                    "token_hash": _digest("device-token", token, settings),
                    "token_hint": token_hint,
                },
            )
        else:
            session.execute(
                text(
                    """
                    INSERT INTO lighthouse.devices(
                      id, tenant_id, owner_user_id, instance_id, label, public_key,
                      token_public_id, token_hash, token_hint
                    ) VALUES (
                      :id, :tenant_id, :owner_user_id, :instance_id, :label, :public_key,
                      :token_public_id, :token_hash, :token_hint
                    )
                    """
                ),
                {
                    "id": device_id,
                    "tenant_id": tenant_id,
                    "owner_user_id": challenge["owner_user_id"],
                    "instance_id": parsed_instance_id,
                    "label": device_label,
                    "public_key": clean_public_key,
                    "token_public_id": token_public_id,
                    "token_hash": _digest("device-token", token, settings),
                    "token_hint": token_hint,
                },
            )
        session.execute(
            text("UPDATE lighthouse.pairing_challenges SET consumed_at = :now WHERE id = :id"),
            {"now": now, "id": challenge["id"]},
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (
                  :tenant_id, :actor_user_id, 'lighthouse.device.enrolled',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "actor_user_id": challenge["owner_user_id"],
                "payload": json.dumps(
                    {"device_id": str(device_id), "instance_id": str(parsed_instance_id)}
                ),
            },
        )
    origin = settings.public_origin.rstrip("/")
    socket_origin = (
        f"wss://{origin.removeprefix('https://')}"
        if origin.startswith("https://")
        else f"ws://{origin.removeprefix('http://')}"
    )
    return {
        "ok": True,
        "device_id": str(device_id),
        "device_token": token,
        "token_hint": token_hint,
        "protocol": PROTOCOL,
        "websocket_url": f"{socket_origin}/api/lighthouse/device/v1/connect",
        "note": (
            "Store the device token in the operating-system credential store; "
            "it is shown once."
        ),
    }


def authenticate_device_token(plain: str, settings: Settings) -> DevicePrincipal:
    match = _DEVICE_RE.fullmatch(str(plain or "").strip())
    if not match:
        raise LighthouseFederationError("Invalid Lighthouse device token", 401)
    tenant_slug, public_id = match.group(1), match.group(2)
    tenant_id = _tenant_for_slug(tenant_slug)
    if tenant_id is None:
        raise LighthouseFederationError("Invalid Lighthouse device token", 401)
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT id, owner_user_id, instance_id, token_hash, status
                    FROM lighthouse.devices WHERE token_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            .mappings()
            .one_or_none()
        )
        if (
            row is None
            or row["status"] != "active"
            or not hmac.compare_digest(
                str(row["token_hash"]), _digest("device-token", plain, settings)
            )
        ):
            raise LighthouseFederationError("Invalid Lighthouse device token", 401)
    return DevicePrincipal(
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        device_id=row["id"],
        owner_user_id=row["owner_user_id"],
        instance_id=row["instance_id"],
    )


def open_device_connection(principal: DevicePrincipal) -> UUID:
    connection_id = uuid4()
    with tenant_session(principal.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO lighthouse.device_connections(
                  id, tenant_id, device_id, protocol_version
                ) VALUES (:id, :tenant_id, :device_id, :protocol)
                """
            ),
            {
                "id": connection_id,
                "tenant_id": principal.tenant_id,
                "device_id": principal.device_id,
                "protocol": PROTOCOL,
            },
        )
        session.execute(
            text(
                """
                UPDATE lighthouse.devices
                SET connected_at = now(), last_seen_at = now()
                WHERE id = :device_id
                """
            ),
            {"device_id": principal.device_id},
        )
    return connection_id


def close_device_connection(
    principal: DevicePrincipal,
    connection_id: UUID,
    *,
    reason: str = "disconnected",
) -> None:
    with tenant_session(principal.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE lighthouse.device_connections
                SET disconnected_at = now(), close_reason = :reason
                WHERE id = :connection_id AND device_id = :device_id
                  AND disconnected_at IS NULL
                """
            ),
            {
                "connection_id": connection_id,
                "device_id": principal.device_id,
                "reason": reason[:500],
            },
        )


def list_devices(actor: ActorContext) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, instance_id, label, status, protocol_version,
                           capabilities, metadata, connected_at, last_seen_at, created_at
                    FROM lighthouse.devices
                    WHERE owner_user_id = :owner_user_id
                    ORDER BY updated_at DESC
                    """
                ),
                {"owner_user_id": actor.user_id},
            )
            .mappings()
            .all()
        )
    return [_device_public(dict(row)) for row in rows]


def revoke_device(actor: ActorContext, device_id: UUID) -> dict[str, object]:
    if actor.auth_kind != "session":
        raise LighthouseFederationError("Revoking a device requires an interactive session", 403)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    UPDATE lighthouse.devices
                    SET status = 'revoked', revoked_at = now()
                    WHERE id = :device_id AND owner_user_id = :owner_user_id
                    RETURNING id, label, revoked_at
                    """
                ),
                {"device_id": device_id, "owner_user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise LighthouseFederationError("Lighthouse device not found", 404)
    return {
        "ok": True,
        "device_id": str(row["id"]),
        "label": row["label"],
        "revoked_at": row["revoked_at"].isoformat(),
    }


def create_remote_run(
    actor: ActorContext,
    *,
    device_id: object,
    goal: object,
    conversation_ref: object = None,
    workspace_ref: object = None,
    client_request_id: object = None,
    read_only: object = True,
) -> tuple[dict[str, object], dict[str, object], UUID]:
    if actor.auth_kind != "session":
        raise LighthouseFederationError(
            "Remote device control requires an interactive session", 403
        )
    if "ai.use" not in actor.permissions:
        raise LighthouseFederationError("Current account cannot use the AI secretary", 403)
    if read_only is not True:
        raise LighthouseFederationError(
            "Federation v1 accepts read-only Runs only; remote write approval is not enabled",
            409,
        )
    parsed_device_id = _parse_uuid(device_id, "device_id")
    clean_goal = _bounded_text(goal, "goal", maximum=16_384)
    clean_conversation = str(conversation_ref or "").strip() or None
    clean_workspace = str(workspace_ref or "").strip() or None
    clean_request_id = str(client_request_id or "").strip() or None
    for field, value, maximum in (
        ("conversation_ref", clean_conversation, 128),
        ("workspace_ref", clean_workspace, 256),
        ("client_request_id", clean_request_id, 160),
    ):
        if value is not None and len(value) > maximum:
            raise LighthouseFederationError(f"{field} is too long")
    policy = {"mode": "read_only", "allow_local_write": False}
    with tenant_session(actor.tenant_id) as session:
        device = (
            session.execute(
                text(
                    """
                    SELECT id FROM lighthouse.devices
                    WHERE id = :device_id AND owner_user_id = :owner_user_id
                      AND status = 'active'
                    """
                ),
                {"device_id": parsed_device_id, "owner_user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        if device is None:
            raise LighthouseFederationError("Active Lighthouse device not found", 404)
        if clean_request_id:
            existing = (
                session.execute(
                    text(
                        """
                        SELECT * FROM lighthouse.runs
                        WHERE owner_user_id = :owner_user_id
                          AND client_request_id = :client_request_id
                        """
                    ),
                    {"owner_user_id": actor.user_id, "client_request_id": clean_request_id},
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                return _run_public(dict(existing)), {}, UUID(int=0)
        run_id = uuid4()
        message_id = uuid4()
        offer_payload: dict[str, object] = {
            "run_id": str(run_id),
            "goal": clean_goal,
            "policy": policy,
        }
        if clean_conversation:
            offer_payload["conversation_ref"] = clean_conversation
        if clean_workspace:
            offer_payload["workspace_ref"] = clean_workspace
        envelope = make_envelope("run.offer", offer_payload, message_id=message_id)
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO lighthouse.runs(
                      id, tenant_id, owner_user_id, device_id, client_request_id,
                      conversation_ref, workspace_ref, goal, policy, status, offered_at
                    ) VALUES (
                      :id, :tenant_id, :owner_user_id, :device_id, :client_request_id,
                      :conversation_ref, :workspace_ref, :goal, CAST(:policy AS jsonb),
                      'offered', now()
                    ) RETURNING *
                    """
                ),
                {
                    "id": run_id,
                    "tenant_id": actor.tenant_id,
                    "owner_user_id": actor.user_id,
                    "device_id": parsed_device_id,
                    "client_request_id": clean_request_id,
                    "conversation_ref": clean_conversation,
                    "workspace_ref": clean_workspace,
                    "goal": clean_goal,
                    "policy": json.dumps(policy),
                },
            )
            .mappings()
            .one()
        )
        session.execute(
            text(
                """
                INSERT INTO lighthouse.outbox(
                  tenant_id, device_id, run_id, message_id, message_type, payload
                ) VALUES (
                  :tenant_id, :device_id, :run_id, :message_id, 'run.offer',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "device_id": parsed_device_id,
                "run_id": run_id,
                "message_id": message_id,
                "payload": json.dumps(offer_payload, ensure_ascii=False),
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (
                  :tenant_id, :actor_user_id, 'lighthouse.run.offered',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": json.dumps(
                    {"run_id": str(run_id), "device_id": str(parsed_device_id), "policy": policy}
                ),
            },
        )
    return _run_public(dict(row)), envelope, message_id


def enqueue_run_control(
    actor: ActorContext,
    run_id: UUID,
    *,
    message_type: str,
    value: object = None,
) -> tuple[dict[str, object], UUID, UUID]:
    if actor.auth_kind != "session":
        raise LighthouseFederationError(
            "Remote device control requires an interactive session", 403
        )
    if message_type not in {"run.input", "run.cancel"}:
        raise LighthouseFederationError("Unsupported Run control message")
    with tenant_session(actor.tenant_id) as session:
        run = (
            session.execute(
                text(
                    """
                    SELECT id, device_id, status FROM lighthouse.runs
                    WHERE id = :run_id AND owner_user_id = :owner_user_id
                    FOR UPDATE
                    """
                ),
                {"run_id": run_id, "owner_user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        if run is None:
            raise LighthouseFederationError("Lighthouse Run not found", 404)
        if run["status"] in {"completed", "failed", "cancelled", "rejected"}:
            raise LighthouseFederationError("Lighthouse Run is already terminal", 409)
        payload: dict[str, object] = {"run_id": str(run_id)}
        if message_type == "run.input":
            payload["text"] = _visible_text(value, "text", maximum=16_384)
        else:
            payload["reason"] = str(value or "Cancelled by user")[:500]
            session.execute(
                text("UPDATE lighthouse.runs SET status = 'cancelling' WHERE id = :run_id"),
                {"run_id": run_id},
            )
        message_id = uuid4()
        envelope = make_envelope(message_type, payload, message_id=message_id)
        session.execute(
            text(
                """
                INSERT INTO lighthouse.outbox(
                  tenant_id, device_id, run_id, message_id, message_type, payload
                ) VALUES (
                  :tenant_id, :device_id, :run_id, :message_id, :message_type,
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "device_id": run["device_id"],
                "run_id": run_id,
                "message_id": message_id,
                "message_type": message_type,
                "payload": json.dumps(payload, ensure_ascii=False),
            },
        )
    return envelope, message_id, run["device_id"]


def pending_outbox(principal: DevicePrincipal, *, limit: int = 100) -> list[dict[str, object]]:
    with tenant_session(principal.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT message_id, message_type, payload
                    FROM lighthouse.outbox
                    WHERE device_id = :device_id AND delivered_at IS NULL
                      AND available_at <= now()
                    ORDER BY id LIMIT :limit
                    """
                ),
                {"device_id": principal.device_id, "limit": limit},
            )
            .mappings()
            .all()
        )
    return [
        make_envelope(row["message_type"], dict(row["payload"]), message_id=row["message_id"])
        for row in rows
    ]


def mark_outbox_delivery(
    tenant_id: UUID,
    message_id: UUID | str,
    *,
    delivered: bool,
    error: str | None = None,
    device_id: UUID | None = None,
) -> None:
    with tenant_session(tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE lighthouse.outbox
                SET delivery_attempts = delivery_attempts + 1,
                    delivered_at = CASE WHEN :delivered THEN now() ELSE delivered_at END,
                    last_error = :last_error
                WHERE message_id = :message_id
                  AND (:device_id IS NULL OR device_id = :device_id)
                """
            ),
            {
                "message_id": message_id,
                "delivered": delivered,
                "last_error": None if delivered or error is None else str(error)[:1000],
                "device_id": device_id,
            },
        )


def _owned_run(session, principal: DevicePrincipal, run_id: UUID) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
                SELECT * FROM lighthouse.runs
                WHERE id = :run_id AND device_id = :device_id
                  AND owner_user_id = :owner_user_id
                FOR UPDATE
                """
            ),
            {
                "run_id": run_id,
                "device_id": principal.device_id,
                "owner_user_id": principal.owner_user_id,
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise LighthouseFederationError("Run does not belong to this device", 403)
    return dict(row)


def _append_event(
    session,
    principal: DevicePrincipal,
    run_id: UUID,
    *,
    event_id: UUID,
    event_type: str,
    payload: dict[str, object],
) -> tuple[int, bool]:
    existing = session.execute(
        text(
            """
            SELECT sequence FROM lighthouse.run_events
            WHERE run_id = :run_id AND event_id = :event_id
            """
        ),
        {"run_id": run_id, "event_id": event_id},
    ).scalar_one_or_none()
    if existing is not None:
        return int(existing), True
    sequence = session.execute(
        text(
            """
            UPDATE lighthouse.runs SET event_cursor = event_cursor + 1
            WHERE id = :run_id RETURNING event_cursor
            """
        ),
        {"run_id": run_id},
    ).scalar_one()
    session.execute(
        text(
            """
            INSERT INTO lighthouse.run_events(
              run_id, tenant_id, device_id, sequence, event_id, event_type, payload
            ) VALUES (
              :run_id, :tenant_id, :device_id, :sequence, :event_id, :event_type,
              CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "run_id": run_id,
            "tenant_id": principal.tenant_id,
            "device_id": principal.device_id,
            "sequence": sequence,
            "event_id": event_id,
            "event_type": event_type[:100],
            "payload": json.dumps(payload, ensure_ascii=False),
        },
    )
    return int(sequence), False


def handle_device_message(
    principal: DevicePrincipal,
    raw: object,
) -> dict[str, object]:
    message = parse_device_message(raw)
    message_id = UUID(str(message["message_id"]))
    message_type = str(message["type"])
    payload = dict(message["payload"])
    if message_type == "message.ack":
        acknowledged_message_id = UUID(str(payload["message_id"]))
        mark_outbox_delivery(
            principal.tenant_id,
            acknowledged_message_id,
            delivered=True,
            device_id=principal.device_id,
        )
        return {
            "message_id": str(message_id),
            "accepted": True,
            "acknowledgement": True,
            "acknowledged_message_id": str(acknowledged_message_id),
        }
    if message_type in {"instance.hello", "instance.heartbeat"}:
        capabilities = payload.get("capabilities") if message_type == "instance.hello" else None
        metadata = payload.get("metadata") if message_type == "instance.hello" else None
        if capabilities is not None and not isinstance(capabilities, list):
            raise LighthouseFederationError("capabilities must be an array")
        if metadata is not None and not isinstance(metadata, dict):
            raise LighthouseFederationError("metadata must be an object")
        with tenant_session(principal.tenant_id) as session:
            session.execute(
                text(
                    """
                    UPDATE lighthouse.devices
                    SET last_seen_at = now(),
                        capabilities = CASE WHEN :has_capabilities
                          THEN CAST(:capabilities AS jsonb) ELSE capabilities END,
                        metadata = CASE WHEN :has_metadata
                          THEN CAST(:metadata AS jsonb) ELSE metadata END
                    WHERE id = :device_id
                    """
                ),
                {
                    "device_id": principal.device_id,
                    "has_capabilities": capabilities is not None,
                    "capabilities": json.dumps(capabilities or []),
                    "has_metadata": metadata is not None,
                    "metadata": json.dumps(metadata or {}),
                },
            )
        return {"message_id": str(message_id), "accepted": True}

    run_id = UUID(str(payload["run_id"]))
    with tenant_session(principal.tenant_id) as session:
        run = _owned_run(session, principal, run_id)
        dedupe_event_id = (
            UUID(str(payload["event_id"])) if message_type == "run.event" else message_id
        )
        existing_sequence = session.execute(
            text(
                """
                SELECT sequence FROM lighthouse.run_events
                WHERE run_id = :run_id AND event_id = :event_id
                """
            ),
            {"run_id": run_id, "event_id": dedupe_event_id},
        ).scalar_one_or_none()
        if existing_sequence is not None:
            return {
                "message_id": str(message_id),
                "accepted": True,
                "run_id": str(run_id),
                "sequence": int(existing_sequence),
                "duplicate": True,
                "previous_status": run["status"],
            }
        if message_type == "run.accepted":
            local_run_ref = str(payload.get("local_run_ref") or "")[:256] or None
            session.execute(
                text(
                    """
                    UPDATE lighthouse.runs
                    SET status = CASE WHEN status IN ('offered', 'queued')
                                      THEN 'accepted' ELSE status END,
                        local_run_ref = COALESCE(:local_run_ref, local_run_ref),
                        accepted_at = COALESCE(accepted_at, now())
                    WHERE id = :run_id
                    """
                ),
                {"run_id": run_id, "local_run_ref": local_run_ref},
            )
            sequence, duplicate = _append_event(
                session,
                principal,
                run_id,
                event_id=message_id,
                event_type="run.accepted",
                payload={"local_run_ref": local_run_ref},
            )
        elif message_type == "run.rejected":
            reason = str(payload.get("reason") or "Run rejected by device")[:2000]
            session.execute(
                text(
                    """
                    UPDATE lighthouse.runs
                    SET status = 'rejected', error = :reason, completed_at = now()
                    WHERE id = :run_id AND status NOT IN ('completed', 'failed', 'cancelled')
                    """
                ),
                {"run_id": run_id, "reason": reason},
            )
            sequence, duplicate = _append_event(
                session,
                principal,
                run_id,
                event_id=message_id,
                event_type="run.rejected",
                payload={"reason": reason},
            )
        elif message_type == "run.event":
            event_id = UUID(str(payload["event_id"]))
            event_type = str(payload.get("event_type") or "run.progress")[:100]
            event_payload = payload.get("data")
            if not isinstance(event_payload, dict):
                event_payload = {"message": str(event_payload or "")[:32_768]}
            session.execute(
                text(
                    """
                    UPDATE lighthouse.runs
                    SET status = CASE WHEN status IN ('offered', 'accepted')
                                      THEN 'running' ELSE status END
                    WHERE id = :run_id
                    """
                ),
                {"run_id": run_id},
            )
            sequence, duplicate = _append_event(
                session,
                principal,
                run_id,
                event_id=event_id,
                event_type=event_type,
                payload=event_payload,
            )
        elif message_type == "operation.approval_required":
            digest = str(payload["operation_digest"])
            presentation = payload.get("presentation")
            if not isinstance(presentation, dict):
                presentation = {}
            approval_id = uuid4()
            session.execute(
                text(
                    """
                    INSERT INTO lighthouse.approvals(
                      id, tenant_id, run_id, device_id, operation_digest,
                      presentation, expires_at
                    ) VALUES (
                      :id, :tenant_id, :run_id, :device_id, :digest,
                      CAST(:presentation AS jsonb), now() + interval '10 minutes'
                    ) ON CONFLICT (tenant_id, run_id, operation_digest) DO NOTHING
                    """
                ),
                {
                    "id": approval_id,
                    "tenant_id": principal.tenant_id,
                    "run_id": run_id,
                    "device_id": principal.device_id,
                    "digest": digest,
                    "presentation": json.dumps(presentation, ensure_ascii=False),
                },
            )
            session.execute(
                text("UPDATE lighthouse.runs SET status = 'awaiting_approval' WHERE id = :run_id"),
                {"run_id": run_id},
            )
            sequence, duplicate = _append_event(
                session,
                principal,
                run_id,
                event_id=message_id,
                event_type="operation.approval_required",
                payload={
                    "operation_digest": digest,
                    "presentation": presentation,
                    "remote_grant_available": False,
                },
            )
        elif message_type == "receipt.committed":
            projection = payload.get("projection")
            if not isinstance(projection, dict):
                projection = {}
            local_ref = _visible_text(
                payload.get("local_receipt_ref"), "local_receipt_ref", maximum=256
            )
            committed_at = datetime.now(UTC)
            session.execute(
                text(
                    """
                    INSERT INTO lighthouse.receipt_projections(
                      id, tenant_id, run_id, device_id, local_receipt_ref,
                      receipt_digest, projection, committed_at
                    ) VALUES (
                      :id, :tenant_id, :run_id, :device_id, :local_ref,
                      :digest, CAST(:projection AS jsonb), :committed_at
                    ) ON CONFLICT (tenant_id, device_id, local_receipt_ref) DO NOTHING
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": principal.tenant_id,
                    "run_id": run_id,
                    "device_id": principal.device_id,
                    "local_ref": local_ref,
                    "digest": payload["receipt_digest"],
                    "projection": json.dumps(projection, ensure_ascii=False),
                    "committed_at": committed_at,
                },
            )
            sequence, duplicate = _append_event(
                session,
                principal,
                run_id,
                event_id=message_id,
                event_type="receipt.committed",
                payload={
                    "local_receipt_ref": local_ref,
                    "receipt_digest": payload["receipt_digest"],
                    "projection": projection,
                },
            )
        else:
            terminal_status = str(payload.get("status") or "completed")
            if terminal_status not in {"completed", "failed", "cancelled"}:
                raise LighthouseFederationError("Invalid terminal Run status")
            result = payload.get("result")
            if result is not None and not isinstance(result, dict):
                result = {"message": str(result)[:32_768]}
            error = str(payload.get("error") or "")[:4000] or None
            session.execute(
                text(
                    """
                    UPDATE lighthouse.runs
                    SET status = :status, result = CAST(:result AS jsonb), error = :error,
                        completed_at = now()
                    WHERE id = :run_id
                    """
                ),
                {
                    "run_id": run_id,
                    "status": terminal_status,
                    "result": json.dumps(result) if result is not None else None,
                    "error": error,
                },
            )
            sequence, duplicate = _append_event(
                session,
                principal,
                run_id,
                event_id=message_id,
                event_type="run.completed",
                payload={"status": terminal_status, "result": result, "error": error},
            )
        session.execute(
            text("UPDATE lighthouse.devices SET last_seen_at = now() WHERE id = :device_id"),
            {"device_id": principal.device_id},
        )
    return {
        "message_id": str(message_id),
        "accepted": True,
        "run_id": str(run_id),
        "sequence": sequence,
        "duplicate": duplicate,
        "previous_status": run["status"],
    }


def get_run(actor: ActorContext, run_id: UUID) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT * FROM lighthouse.runs
                    WHERE id = :run_id AND owner_user_id = :owner_user_id
                    """
                ),
                {"run_id": run_id, "owner_user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise LighthouseFederationError("Lighthouse Run not found", 404)
    return _run_public(dict(row))


def list_run_events(
    actor: ActorContext,
    run_id: UUID,
    *,
    after_sequence: int = 0,
    limit: int = 200,
) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        owned = session.execute(
            text(
                """
                SELECT 1 FROM lighthouse.runs
                WHERE id = :run_id AND owner_user_id = :owner_user_id
                """
            ),
            {"run_id": run_id, "owner_user_id": actor.user_id},
        ).scalar_one_or_none()
        if owned is None:
            raise LighthouseFederationError("Lighthouse Run not found", 404)
        rows = (
            session.execute(
                text(
                    """
                    SELECT sequence, event_id, event_type, payload, created_at
                    FROM lighthouse.run_events
                    WHERE run_id = :run_id AND sequence > :after_sequence
                    ORDER BY sequence LIMIT :limit
                    """
                ),
                {"run_id": run_id, "after_sequence": after_sequence, "limit": limit},
            )
            .mappings()
            .all()
        )
    return [
        {
            "sequence": int(row["sequence"]),
            "event_id": str(row["event_id"]),
            "type": row["event_type"],
            "payload": dict(row["payload"]),
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]
