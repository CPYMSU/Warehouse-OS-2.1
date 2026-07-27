"""Ports and PostgreSQL adapter used by terminal command handlers.

Command handlers depend on the small reader/writer interfaces below instead
of raw SQL or a particular database driver.  Replacing PostgreSQL therefore
means implementing these ports and keeping the terminal/AI contracts stable.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol
from uuid import UUID, uuid4

from sqlalchemy import text

from app.db.session import tenant_session

if TYPE_CHECKING:
    from app.api.deps import ActorContext


class WarehouseReader(Protocol):
    def list_active(self, tenant_id: UUID) -> list[dict[str, object]]: ...


class CommandAuditWriter(Protocol):
    def record(
        self,
        *,
        actor: ActorContext,
        command: str,
        tool_name: str,
        origin: str,
        status: str,
        request: Mapping[str, object],
        response: Mapping[str, object],
    ) -> str: ...


class PostgreSQLWarehouseReader:
    def list_active(self, tenant_id: UUID) -> list[dict[str, object]]:
        with tenant_session(tenant_id) as session:
            rows = session.execute(
                text(
                    """
                    SELECT id::text AS id, code, name, warehouse_type, address,
                           lat::text AS lat, lng::text AS lng,
                           capacity_usage::text AS capacity_usage, active
                    FROM warehouse.warehouses
                    WHERE active
                    ORDER BY name, code
                    """
                )
            ).mappings().all()
        return [dict(row) for row in rows]


class PostgreSQLCommandAuditWriter:
    def record(
        self,
        *,
        actor: ActorContext,
        command: str,
        tool_name: str,
        origin: str,
        status: str,
        request: Mapping[str, object],
        response: Mapping[str, object],
    ) -> str:
        execution_id = str(uuid4())
        payload = {
            "execution_id": execution_id,
            "command": command,
            "tool_name": tool_name,
            "origin": origin,
            "status": status,
        }
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text(
                    """
                    INSERT INTO terminal.command_executions(
                      id, tenant_id, actor_user_id, command, tool_name, origin,
                      status, request, response
                    ) VALUES (
                      :id, :tenant_id, :actor_user_id, :command, :tool_name, :origin,
                      :status, CAST(:request AS jsonb), CAST(:response AS jsonb)
                    )
                    """
                ),
                {
                    "id": execution_id,
                    "tenant_id": str(actor.tenant_id),
                    "actor_user_id": str(actor.user_id),
                    "command": command,
                    "tool_name": tool_name,
                    "origin": origin,
                    "status": status,
                    "request": json.dumps(dict(request), ensure_ascii=False, default=str),
                    "response": json.dumps(dict(response), ensure_ascii=False, default=str),
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                    VALUES (:tenant_id, :actor_user_id, 'terminal.command.executed',
                            CAST(:payload AS jsonb))
                    """
                ),
                {
                    "tenant_id": str(actor.tenant_id),
                    "actor_user_id": str(actor.user_id),
                    "payload": json.dumps(payload, ensure_ascii=False),
                },
            )
        return execution_id


def warehouse_reader() -> WarehouseReader:
    return PostgreSQLWarehouseReader()


def command_audit_writer() -> CommandAuditWriter:
    return PostgreSQLCommandAuditWriter()
