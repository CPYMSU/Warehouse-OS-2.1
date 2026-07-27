"""Idempotently restore selected Bonfire identities from an encrypted input stream.

The caller supplies JSON through standard input.  It is intentionally designed
so the legacy password hashes never need to be printed, saved to a work file,
or placed in a command line.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from app.db.session import system_session, tenant_session
from app.services.templates import provision_tenant_template

_EXPECTED_USERNAMES = frozenset(
    {"c_peiyuan@icloud.com", "alexzxczd@icloud.com", "l_zhiheng@icloud.com"}
)
_LI_USERNAME = "l_zhiheng@icloud.com"


@dataclass(frozen=True)
class LegacyUser:
    username: str
    display_name: str
    password_hash: str
    topology_level: int
    topology_title: str


@dataclass(frozen=True)
class BonfirePayload:
    tenant_name: str
    template_key: str
    users: tuple[LegacyUser, ...]


def parse_payload(raw: object) -> BonfirePayload:
    if not isinstance(raw, dict):
        raise ValueError("legacy input must be a JSON object")
    tenant = raw.get("tenant")
    users = raw.get("users")
    if not isinstance(tenant, dict) or str(tenant.get("slug") or "") != "bonfire":
        raise ValueError("legacy input must describe the Bonfire tenant")
    if not isinstance(users, list) or len(users) != 3:
        raise ValueError("legacy input must contain exactly three Bonfire users")
    parsed: list[LegacyUser] = []
    for row in users:
        if not isinstance(row, dict):
            raise ValueError("legacy user entry is invalid")
        username = str(row.get("username") or "").strip().lower()
        display_name = str(row.get("display_name") or "").strip()
        password_hash = str(row.get("password_hash") or "")
        level = int(row.get("topology_level") or 0)
        title = str(row.get("topology_title") or "").strip()
        if not username or not display_name or not password_hash or not 1 <= level <= 10:
            raise ValueError("legacy user is missing required identity fields")
        parsed.append(LegacyUser(username, display_name, password_hash, level, title))
    usernames = {user.username for user in parsed}
    if usernames != _EXPECTED_USERNAMES:
        raise ValueError("legacy input does not match the approved Bonfire identities")
    return BonfirePayload(
        tenant_name=str(tenant.get("name") or "Bonfire").strip(),
        template_key=str(tenant.get("industry_template") or "").strip(),
        users=tuple(parsed),
    )


def _ensure_tenant(payload: BonfirePayload) -> tuple[UUID, bool]:
    with system_session() as session:
        tenant = session.execute(
            text("SELECT id FROM iam.tenants WHERE slug = 'bonfire'")
        ).mappings().one_or_none()
        if tenant is not None:
            return tenant["id"], False
        tenant_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, 'bonfire', :name, :template_key)
                """
            ),
            {"id": tenant_id, "name": payload.tenant_name, "template_key": payload.template_key},
        )
    return tenant_id, True


def _ensure_users(users: tuple[LegacyUser, ...]) -> dict[str, UUID]:
    user_ids: dict[str, UUID] = {}
    with system_session() as session:
        for user in users:
            row = session.execute(
                text("SELECT id FROM iam.users WHERE username = :username"),
                {"username": user.username},
            ).mappings().one_or_none()
            if row is None:
                user_id = uuid4()
                session.execute(
                    text(
                        """
                        INSERT INTO iam.users(id, username, display_name, password_hash)
                        VALUES (:id, :username, :display_name, :password_hash)
                        """
                    ),
                    {
                        "id": user_id,
                        "username": user.username,
                        "display_name": user.display_name,
                        "password_hash": user.password_hash,
                    },
                )
            else:
                user_id = row["id"]
            user_ids[user.username] = user_id
    return user_ids


def _provision_if_empty(tenant_id: UUID, payload: BonfirePayload) -> None:
    with tenant_session(tenant_id) as session:
        has_positions = session.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM iam.position_profiles WHERE tenant_id = :tenant_id)"
            ),
            {"tenant_id": tenant_id},
        ).scalar_one()
        if not has_positions:
            provision_tenant_template(
                session,
                tenant_id=tenant_id,
                tenant_name=payload.tenant_name,
                template_key=payload.template_key,
            )


def _closest_position(session: Any, tenant_id: UUID, level: int, title: str) -> str:
    return str(
        session.execute(
            text(
                """
                SELECT position_code
                FROM iam.position_profiles
                WHERE tenant_id = :tenant_id AND active
                ORDER BY
                  CASE WHEN name = :title THEN 0 ELSE 1 END,
                  abs(role_level - :level), is_manager DESC, position_code
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "level": level, "title": title},
        ).scalar_one()
    )


def _l10_primary_position(session: Any, tenant_id: UUID) -> str:
    return str(
        session.execute(
            text(
                """
                SELECT position_code
                FROM iam.position_profiles
                WHERE tenant_id = :tenant_id AND active AND role_level = 10
                ORDER BY position_code
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        ).scalar_one()
    )


def _ensure_general_manager_position(session: Any, tenant_id: UUID) -> str:
    """Add Bonfire's tenant-specific L10 general-manager appointment once."""
    position_code = "general_manager"
    exists = session.execute(
        text(
            """
            SELECT 1 FROM iam.position_profiles
            WHERE tenant_id = :tenant_id AND position_code = :position_code
            """
        ),
        {"tenant_id": tenant_id, "position_code": position_code},
    ).scalar_one_or_none()
    if exists is None:
        session.execute(
            text(
                """
                INSERT INTO iam.position_profiles(
                  id, tenant_id, template_key, position_code, department_code, name,
                  role_name, role_level, is_manager, permissions, database_access,
                  navigation_defaults, public_entry, case_roles
                )
                SELECT :id, tenant_id, template_key, :position_code, 'company', '總經理',
                       '總經理', 10, true, permissions, database_access,
                       navigation_defaults, public_entry, case_roles
                FROM iam.position_profiles
                WHERE tenant_id = :tenant_id AND position_code = 'lab_system_admin'
                """
            ),
            {"id": uuid4(), "tenant_id": tenant_id, "position_code": position_code},
        )
    return position_code


def restore(payload: BonfirePayload) -> dict[str, int | str]:
    tenant_id, tenant_created = _ensure_tenant(payload)
    user_ids = _ensure_users(payload.users)
    _provision_if_empty(tenant_id, payload)
    restored_memberships = 0
    with tenant_session(tenant_id) as session:
        system_admin_position = _l10_primary_position(session, tenant_id)
        general_manager_position = _ensure_general_manager_position(session, tenant_id)
        for user in payload.users:
            user_id = user_ids[user.username]
            source_position = _closest_position(
                session, tenant_id, user.topology_level, user.topology_title
            )
            position_code = (
                general_manager_position if user.username == _LI_USERNAME else system_admin_position
            )
            topology_title = "L10 總經理" if user.username == _LI_USERNAME else "L10 系統管理員"
            session.execute(
                text(
                    """
                    INSERT INTO iam.memberships(
                      tenant_id, user_id, position_code, active, role_level, topology_level,
                      topology_title
                    ) VALUES (
                      :tenant_id, :user_id, :position_code, true, 10, 10, :topology_title
                    )
                    ON CONFLICT (tenant_id, user_id) DO UPDATE SET
                      position_code = EXCLUDED.position_code,
                      active = true,
                      role_level = EXCLUDED.role_level,
                      topology_level = EXCLUDED.topology_level,
                      topology_title = EXCLUDED.topology_title
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "position_code": position_code,
                    "topology_title": topology_title,
                },
            )
            session.execute(
                text(
                    """
                    UPDATE iam.membership_positions
                    SET appointment_type = 'concurrent'
                    WHERE tenant_id = :tenant_id AND user_id = :user_id
                      AND appointment_type = 'primary' AND position_code <> :position_code
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id, "position_code": position_code},
            )
            session.execute(
                text(
                    """
                    INSERT INTO iam.membership_positions(
                      tenant_id, user_id, position_code, appointment_type, active
                    ) VALUES (:tenant_id, :user_id, :position_code, 'primary', true)
                    ON CONFLICT (tenant_id, user_id, position_code) DO UPDATE SET
                      appointment_type = 'primary', active = true
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id, "position_code": position_code},
            )
            concurrent_positions = {source_position}
            if user.username == _LI_USERNAME:
                concurrent_positions.add(system_admin_position)
            for concurrent_position in concurrent_positions - {position_code}:
                session.execute(
                    text(
                        """
                        INSERT INTO iam.membership_positions(
                          tenant_id, user_id, position_code, appointment_type, active
                        ) VALUES (:tenant_id, :user_id, :position_code, 'concurrent', true)
                        ON CONFLICT (tenant_id, user_id, position_code) DO UPDATE SET
                          appointment_type = 'concurrent', active = true
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "position_code": concurrent_position,
                    },
                )
            session.execute(
                text(
                    """
                    INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                    VALUES (
                      :tenant_id, :user_id, 'legacy.bonfire.identity.restored',
                      CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "payload": json.dumps(
                        {"source": "vultr-legacy", "legacy_tenant": "bonfire"},
                        ensure_ascii=False,
                    ),
                },
            )
            restored_memberships += 1
    return {
        "tenant": "bonfire",
        "tenant_created": int(tenant_created),
        "users": len(user_ids),
        "memberships_restored": restored_memberships,
    }


def main() -> None:
    payload = parse_payload(json.load(sys.stdin))
    print(json.dumps(restore(payload), ensure_ascii=False))


if __name__ == "__main__":
    main()
