from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import tenant_session

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class PositionIdentity:
    position_code: str
    name: str
    role_level: int
    appointment_type: str


@dataclass(frozen=True)
class ActorContext:
    user_id: UUID
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str
    industry_template_key: str
    username: str
    display_name: str
    role_level: int
    topology_level: int
    topology_title: str | None
    permissions: frozenset[str] = frozenset()
    identities: tuple[PositionIdentity, ...] = ()
    auth_kind: str = "session"
    credential_id: int | None = None
    credential_scopes: frozenset[str] = frozenset()

    @property
    def user_payload(self) -> dict[str, object]:
        return {
            "id": str(self.user_id),
            "global_user_id": str(self.user_id),
            "username": self.username,
            "display_name": self.display_name,
            "role_level": self.role_level,
            "topology_level": self.topology_level,
            "topology_title": self.topology_title,
            "permissions": sorted(self.permissions),
            "identities": [
                {
                    "position_code": identity.position_code,
                    "name": identity.name,
                    "role_level": identity.role_level,
                    "appointment_type": identity.appointment_type,
                }
                for identity in self.identities
            ],
        }


_internal_actor: ContextVar[ActorContext | None] = ContextVar(
    "warehouse_internal_actor",
    default=None,
)


@contextmanager
def internal_actor_scope(actor: ActorContext) -> Generator[None, None, None]:
    """Bind an already-authenticated actor to one in-process ASGI dispatch.

    This context has no HTTP representation and therefore cannot be supplied by
    a client.  It lets the company AI projection retain its complete
    current-tenant authority while native route dependencies continue to use
    the ordinary ``current_actor`` boundary.
    """

    token = _internal_actor.set(actor)
    try:
        yield
    finally:
        _internal_actor.reset(token)


def _permission_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value if isinstance(item, str) and item.strip()}


def _capped_position_permissions(
    position_rows: list[dict[str, object]],
    unit_rows: list[dict[str, object]],
    *,
    role_level: int,
) -> tuple[set[str], set[str] | None]:
    """Apply ancestor department ceilings to a member's composite appointments.

    L10 is deliberately exempt: a high-level concurrent appointment must not
    be silently downgraded by the department where another appointment sits.
    For other members each position is clipped by its own department chain,
    then all active positions are combined.
    """
    all_permissions: set[str] = set()
    if role_level >= 10:
        for position in position_rows:
            all_permissions.update(_permission_set(position.get("permissions")))
        return all_permissions, None

    units_by_code = {str(unit["unit_code"]): unit for unit in unit_rows}

    def ceiling_for(department_code: str) -> set[str] | None:
        ceiling: set[str] | None = None
        current = units_by_code.get(department_code)
        seen: set[str] = set()
        while current is not None and str(current["unit_code"]) not in seen:
            seen.add(str(current["unit_code"]))
            if bool(current.get("permission_ceiling_enabled")):
                values = _permission_set(current.get("permission_ceiling"))
                ceiling = values if ceiling is None else ceiling.intersection(values)
            parent_code = current.get("parent_unit_code")
            current = units_by_code.get(str(parent_code)) if parent_code else None
        return ceiling

    direct_allow_ceiling: set[str] = set()
    has_unrestricted_position = not position_rows
    for position in position_rows:
        permissions = _permission_set(position.get("permissions"))
        ceiling = ceiling_for(str(position["department_code"]))
        if ceiling is None:
            has_unrestricted_position = True
        else:
            permissions.intersection_update(ceiling)
            direct_allow_ceiling.update(ceiling)
        all_permissions.update(permissions)
    return all_permissions, None if has_unrestricted_position else direct_allow_ceiling


def _load_actor(user_id: UUID, tenant_id: UUID) -> ActorContext:
    """Reload the complete live multi-position authority for one tenant identity."""
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                SELECT u.id AS user_id, u.username, u.display_name,
                       t.id AS tenant_id, t.slug AS tenant_slug, t.name AS tenant_name,
                       t.industry_template_key,
                       m.role_level, m.topology_level, m.topology_title,
                       COALESCE((
                         SELECT jsonb_agg(DISTINCT permission_row.permission_key)
                         FROM iam.membership_positions AS mp
                         JOIN iam.position_profiles AS pp
                           ON pp.tenant_id = mp.tenant_id
                          AND pp.position_code = mp.position_code
                         CROSS JOIN LATERAL jsonb_array_elements_text(pp.permissions)
                           AS permission_row(permission_key)
                         WHERE mp.tenant_id = m.tenant_id AND mp.user_id = m.user_id
                           AND mp.active AND pp.active
                       ), '[]'::jsonb) AS position_permissions,
                       COALESCE((
                         SELECT jsonb_agg(
                           jsonb_build_object(
                             'position_code', pp.position_code,
                             'name', pp.name,
                             'role_level', pp.role_level,
                             'appointment_type', mp.appointment_type
                           ) ORDER BY
                             CASE mp.appointment_type WHEN 'primary' THEN 0 ELSE 1 END,
                             pp.role_level DESC, pp.position_code
                         )
                         FROM iam.membership_positions AS mp
                         JOIN iam.position_profiles AS pp
                           ON pp.tenant_id = mp.tenant_id
                          AND pp.position_code = mp.position_code
                         WHERE mp.tenant_id = m.tenant_id AND mp.user_id = m.user_id
                           AND mp.active AND pp.active
                       ), '[]'::jsonb) AS position_identities,
                       COALESCE((
                         SELECT jsonb_agg(DISTINCT rp.permission_key)
                         FROM iam.membership_roles AS mr
                         JOIN iam.role_permissions AS rp
                           ON rp.tenant_id = mr.tenant_id AND rp.role_id = mr.role_id
                         WHERE mr.tenant_id = m.tenant_id AND mr.user_id = m.user_id
                       ), '[]'::jsonb) AS assigned_permissions,
                       COALESCE((
                         SELECT allow_keys
                         FROM iam.membership_permission_overrides AS mpo
                         WHERE mpo.tenant_id = m.tenant_id AND mpo.user_id = m.user_id
                       ), '[]'::jsonb) AS direct_allow_permissions,
                       COALESCE((
                         SELECT deny_keys
                         FROM iam.membership_permission_overrides AS mpo
                         WHERE mpo.tenant_id = m.tenant_id AND mpo.user_id = m.user_id
                       ), '[]'::jsonb) AS direct_deny_permissions
                FROM iam.users AS u
                JOIN iam.memberships AS m ON m.user_id = u.id
                JOIN iam.tenants AS t ON t.id = m.tenant_id
                LEFT JOIN iam.position_profiles AS pp
                  ON pp.tenant_id = m.tenant_id AND pp.position_code = m.position_code
                WHERE u.id = :user_id AND m.tenant_id = :tenant_id
                  AND u.active AND m.active AND t.status = 'active'
                """
                ),
                {"user_id": user_id, "tenant_id": tenant_id},
            )
            .mappings()
            .one_or_none()
        )
        position_rows: list[dict[str, object]] = []
        unit_rows: list[dict[str, object]] = []
        if row is not None:
            position_rows = [
                dict(item)
                for item in session.execute(
                    text(
                        """
                        SELECT pp.position_code, pp.department_code, pp.permissions
                        FROM iam.membership_positions AS mp
                        JOIN iam.position_profiles AS pp
                          ON pp.tenant_id = mp.tenant_id
                         AND pp.position_code = mp.position_code
                        WHERE mp.user_id = :user_id AND mp.active AND pp.active
                        """
                    ),
                    {"user_id": user_id},
                )
                .mappings()
                .all()
            ]
            unit_rows = [
                dict(item)
                for item in session.execute(
                    text(
                        """
                        SELECT ou.unit_code, ou.parent_unit_code,
                               COALESCE(dap.permission_ceiling_enabled, false)
                                 AS permission_ceiling_enabled,
                               COALESCE(dap.permission_ceiling, '[]'::jsonb)
                                 AS permission_ceiling
                        FROM iam.organizational_units AS ou
                        LEFT JOIN iam.department_access_policies AS dap
                          ON dap.tenant_id = ou.tenant_id AND dap.org_unit_id = ou.id
                        """
                    )
                )
                .mappings()
                .all()
            ]
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer valid",
        )
    position_permissions, direct_allow_ceiling = _capped_position_permissions(
        position_rows,
        unit_rows,
        role_level=int(row["role_level"]),
    )
    assigned_permissions = row["assigned_permissions"]
    direct_allow_permissions = _permission_set(row["direct_allow_permissions"])
    if direct_allow_ceiling is not None:
        direct_allow_permissions.intersection_update(direct_allow_ceiling)
    direct_deny_permissions = row["direct_deny_permissions"]
    identities = tuple(
        PositionIdentity(
            position_code=str(identity["position_code"]),
            name=str(identity["name"]),
            role_level=int(identity["role_level"]),
            appointment_type=str(identity["appointment_type"]),
        )
        for identity in (row["position_identities"] or [])
        if isinstance(identity, dict)
    )
    permissions = frozenset(
        str(permission)
        for permission in [
            *position_permissions,
            *(assigned_permissions or []),
            *direct_allow_permissions,
        ]
        if isinstance(permission, str) and permission.strip()
    ).difference(str(permission) for permission in (direct_deny_permissions or []))
    return ActorContext(
        user_id=row["user_id"],
        tenant_id=row["tenant_id"],
        tenant_slug=row["tenant_slug"],
        tenant_name=row["tenant_name"],
        industry_template_key=row["industry_template_key"],
        username=row["username"],
        display_name=row["display_name"],
        role_level=int(row["role_level"]),
        topology_level=int(row["topology_level"]),
        topology_title=row["topology_title"],
        permissions=permissions,
        identities=identities,
    )


def _runtime_api_scope(request: Request) -> str | None:
    """Return the only Runtime-key audience accepted for this public request."""
    path = request.url.path
    method = request.method.upper()
    if method == "GET" and path == "/api/auth/me":
        return None
    if path.startswith("/api/cli/"):
        return "terminal"
    if path.startswith(("/api/agent/", "/api/ai/", "/api/hosting/")):
        return "assistant"
    if path.startswith("/api/research/"):
        return "research"
    if path.startswith("/api/civilization/"):
        return "civilization"
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Runtime API Key audience does not include this endpoint",
    )


def current_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> ActorContext:
    bound_actor = _internal_actor.get()
    if bound_actor is not None:
        return bound_actor
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials.strip()
    if token.startswith("wsk_"):
        from app.services.runtime_api_keys import (
            SCOPE_PERMISSIONS,
            RuntimeApiKeyError,
            authenticate_runtime_api_key,
        )

        try:
            credential = authenticate_runtime_api_key(token, settings)
        except RuntimeApiKeyError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        required_scope = _runtime_api_scope(request)
        if required_scope is not None and required_scope not in credential.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Runtime API Key is missing the {required_scope} scope",
            )
        actor = _load_actor(credential.user_id, credential.tenant_id)
        if required_scope is not None:
            required_permissions = SCOPE_PERMISSIONS[required_scope]
            if not any(permission in actor.permissions for permission in required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Runtime API access was withdrawn with " + " or ".join(required_permissions)
                    ),
                )
        return replace(
            actor,
            auth_kind="runtime_api_key",
            credential_id=credential.key_id,
            credential_scopes=credential.scopes,
        )
    user_id, tenant_id = decode_access_token(settings=settings, token=token)
    return _load_actor(user_id, tenant_id)
