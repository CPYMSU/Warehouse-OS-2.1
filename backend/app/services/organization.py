# ruff: noqa: E501
"""Tenant-scoped organisation, authority and navigation services for V2.

The browser receives a projection of the tenant organisation; it never becomes
the authority for membership, role or permission changes.  All reads and
writes below happen inside ``tenant_session`` so PostgreSQL RLS remains the
last isolation boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import tenant_session
from app.services.templates import (
    get_template_detail,
    get_template_summary,
    list_template_summaries,
)
from app.templates.industry_blueprints import (
    BLUEPRINT_PERMISSION_KEYS,
    VALID_DEPARTMENT_TYPES,
    blueprint_nav_defaults,
)

NAVIGATION_CATALOG: tuple[dict[str, object], ...] = (
    {"id": "tasks", "idx": "00", "label": "TASK", "group": "工作"},
    {"id": "dashboard", "idx": "01", "label": "總覽", "group": "工作"},
    {"id": "inventory", "idx": "02", "label": "庫存", "group": "倉儲"},
    {"id": "inbound", "idx": "03", "label": "入庫", "group": "倉儲"},
    {"id": "outbound", "idx": "04", "label": "出庫", "group": "倉儲"},
    {"id": "shipments", "idx": "05", "label": "在途", "group": "倉儲"},
    {"id": "alerts", "idx": "06", "label": "預警", "group": "倉儲"},
    {"id": "stocktake", "idx": "07", "label": "盤點", "group": "倉儲"},
    {"id": "erp", "idx": "08", "label": "ERP", "group": "業務"},
    {"id": "finance", "idx": "09", "label": "財務", "group": "業務"},
    {"id": "assets", "idx": "10", "label": "資產", "group": "業務"},
    {"id": "procurement", "idx": "11", "label": "採購", "group": "業務"},
    {"id": "legal", "idx": "12", "label": "法務", "group": "業務"},
    {"id": "gis", "idx": "13", "label": "地圖", "group": "業務"},
    {"id": "reports", "idx": "14", "label": "報表", "group": "業務"},
    {"id": "perms", "idx": "15", "label": "權限", "group": "治理"},
    {"id": "logs", "idx": "16", "label": "審計", "group": "治理"},
    {"id": "cases", "idx": "17", "label": "檔案", "group": "治理"},
    {"id": "settings", "idx": "18", "label": "設置", "group": "治理"},
    {"id": "terminal", "idx": "19", "label": "終端", "group": "治理"},
)
NAVIGATION_IDS = frozenset(str(item["id"]) for item in NAVIGATION_CATALOG)

NAV_PERMISSION_RULES: dict[str, tuple[str, ...]] = {
    "tasks": ("tasks.read",),
    "dashboard": ("overview.read",),
    "inventory": ("inventory.read",),
    "inbound": ("inventory.read", "inventory.inbound"),
    "outbound": ("inventory.read", "inventory.outbound"),
    "shipments": ("inventory.read",),
    "alerts": ("alerts.read",),
    "stocktake": ("inventory.read",),
    "erp": ("erp.read",),
    "finance": ("finance.read",),
    "procurement": ("procurement.workflow.use",),
    "legal": ("legal.manage",),
    "gis": ("gis.read",),
    "reports": ("reports.read",),
    "logs": ("audit.read",),
    "settings": ("settings.manage",),
    "terminal": ("terminal.use",),
}
NAV_PERMISSION_ANY: dict[str, tuple[str, ...]] = {
    "assets": ("assets.read", "asset_mgmt.read"),
    "cases": ("cases.read", "records.read"),
    "perms": (
        "permissions.topology.read",
        "users.manage",
        "permissions.topology.manage",
        "settings.manage",
    ),
}


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [value]
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _uuid(value: object, *, label: str = "id") -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid {label}"
        ) from exc


def _permission(actor: ActorContext, *keys: str) -> bool:
    return actor.role_level >= 10 or any(key in actor.permissions for key in keys)


def _require(actor: ActorContext, *keys: str) -> None:
    if not _permission(actor, *keys):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _can_manage_organization(actor: ActorContext) -> bool:
    return _permission(actor, "users.manage", "settings.manage")


def _can_manage_permissions(actor: ActorContext) -> bool:
    return _permission(actor, "users.manage", "permissions.topology.manage", "settings.manage")


def _audit(
    session: Session, actor: ActorContext, event_type: str, payload: dict[str, object]
) -> None:
    session.execute(
        text("""
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (:tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb))
        """),
        {
            "tenant_id": actor.tenant_id,
            "actor_user_id": actor.user_id,
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _slug(value: str, *, prefix: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return f"{prefix}-{compact[:42] or 'unit'}-{uuid4().hex[:7]}"


def _validated(values: object, allowed: frozenset[str], *, label: str) -> list[str]:
    rows = _strings(values)
    unknown = sorted(set(rows) - allowed)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown {label}: {', '.join(unknown)}",
        )
    return rows


def _nav_entitled(module_id: str, permissions: set[str], *, level: int) -> bool:
    if level >= 10:
        return module_id in NAVIGATION_IDS
    all_required = NAV_PERMISSION_RULES.get(module_id, ())
    any_required = NAV_PERMISSION_ANY.get(module_id, ())
    return all(item in permissions for item in all_required) and (
        not any_required or any(item in permissions for item in any_required)
    )


def _template_blueprint(template_key: str) -> dict[str, object]:
    detail = get_template_detail(template_key)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Industry template not found"
        )
    blueprint = detail.get("blueprint")
    if not isinstance(blueprint, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Industry template is invalid"
        )
    return detail


def _snapshot(session: Session) -> dict[str, object]:
    units = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT id, unit_code, name, name_en, description, unit_type, parent_unit_code,
               active, template_key, manager_user_id, created_at, updated_at
        FROM iam.organizational_units ORDER BY unit_type DESC, name, unit_code
    """)
        )
        .mappings()
        .all()
    ]
    positions = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT id, position_code, department_code, name, name_en, role_name, role_level,
               is_manager, permissions, navigation_defaults, database_access, active,
               template_key, created_at, updated_at
        FROM iam.position_profiles ORDER BY role_level DESC, name, position_code
    """)
        )
        .mappings()
        .all()
    ]
    memberships = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT m.user_id, m.position_code, m.active AS membership_active, m.role_level,
               m.topology_level, m.topology_title, m.created_at AS membership_created_at,
               u.username, u.display_name, u.active AS user_active, u.created_at
        FROM iam.memberships AS m JOIN iam.users AS u ON u.id = m.user_id
        ORDER BY m.topology_level DESC, u.display_name, u.username
    """)
        )
        .mappings()
        .all()
    ]
    appointments = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT user_id, position_code, appointment_type, active, created_at
        FROM iam.membership_positions ORDER BY appointment_type, position_code
    """)
        )
        .mappings()
        .all()
    ]
    policy_rows = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT org_unit_id, permission_ceiling_enabled, permission_ceiling,
               navigation_ceiling_enabled, navigation_ceiling
        FROM iam.department_access_policies
    """)
        )
        .mappings()
        .all()
    ]
    position_policy_rows = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT position_id, navigation_default_enabled, navigation_default
        FROM iam.position_navigation_policies
    """)
        )
        .mappings()
        .all()
    ]
    permission_overrides = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT user_id, allow_keys, deny_keys FROM iam.membership_permission_overrides
    """)
        )
        .mappings()
        .all()
    ]
    navigation_overrides = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT user_id, allow_modules, deny_modules FROM iam.membership_navigation_overrides
    """)
        )
        .mappings()
        .all()
    ]
    role_permissions = [
        dict(row)
        for row in session.execute(
            text("""
        SELECT mr.user_id, rp.permission_key
        FROM iam.membership_roles AS mr
        JOIN iam.role_permissions AS rp ON rp.tenant_id = mr.tenant_id AND rp.role_id = mr.role_id
    """)
        )
        .mappings()
        .all()
    ]
    return {
        "units": units,
        "positions": positions,
        "memberships": memberships,
        "appointments": appointments,
        "department_policies": policy_rows,
        "position_policies": position_policy_rows,
        "permission_overrides": permission_overrides,
        "navigation_overrides": navigation_overrides,
        "role_permissions": role_permissions,
    }


def _projection(snapshot: dict[str, object]) -> dict[str, object]:
    units = list(snapshot["units"])
    positions = list(snapshot["positions"])
    memberships = list(snapshot["memberships"])
    unit_by_code = {str(unit["unit_code"]): unit for unit in units}
    unit_by_id = {str(unit["id"]): unit for unit in units}
    position_by_code = {str(position["position_code"]): position for position in positions}
    unit_id_by_code = {str(unit["unit_code"]): str(unit["id"]) for unit in units}
    policies = {str(row["org_unit_id"]): row for row in snapshot["department_policies"]}
    position_policies = {str(row["position_id"]): row for row in snapshot["position_policies"]}
    permission_overrides = {str(row["user_id"]): row for row in snapshot["permission_overrides"]}
    navigation_overrides = {str(row["user_id"]): row for row in snapshot["navigation_overrides"]}

    appointments_by_user: dict[str, list[dict[str, object]]] = defaultdict(list)
    for appointment in snapshot["appointments"]:
        if appointment["active"]:
            appointments_by_user[str(appointment["user_id"])].append(appointment)
    role_permissions_by_user: dict[str, set[str]] = defaultdict(set)
    for row in snapshot["role_permissions"]:
        role_permissions_by_user[str(row["user_id"])].add(str(row["permission_key"]))

    def chain(unit_id: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        seen: set[str] = set()
        current = unit_by_id.get(unit_id)
        while current is not None and str(current["id"]) not in seen:
            rows.append(current)
            seen.add(str(current["id"]))
            parent_code = current.get("parent_unit_code")
            current = unit_by_code.get(str(parent_code)) if parent_code else None
        return rows

    def ceiling_for(unit_id: str, key: str) -> set[str] | None:
        ceiling: set[str] | None = None
        enabled_key = f"{key}_enabled"
        values_key = key
        for unit in chain(unit_id):
            row = policies.get(str(unit["id"]))
            if row and bool(row.get(enabled_key)):
                values = set(_strings(row.get(values_key)))
                ceiling = values if ceiling is None else ceiling.intersection(values)
        return ceiling

    def identities_for(member: dict[str, object]) -> list[dict[str, object]]:
        identities = appointments_by_user.get(str(member["user_id"]), [])
        if not identities and member.get("position_code"):
            identities = [
                {
                    "position_code": member["position_code"],
                    "appointment_type": "primary",
                    "active": True,
                }
            ]
        return [
            identity
            for identity in identities
            if position_by_code.get(str(identity["position_code"]))
            and position_by_code[str(identity["position_code"])].get("active")
        ]

    def authority_for(
        member: dict[str, object],
    ) -> tuple[set[str], list[str], list[dict[str, object]]]:
        level = int(member["role_level"])
        identities = identities_for(member)
        position_permissions: set[str] = set()
        nav_modules: set[str] = set()
        has_unrestricted_department = False
        direct_allow_ceiling: set[str] = set()
        identity_rows: list[dict[str, object]] = []
        for identity in identities:
            position = position_by_code[str(identity["position_code"])]
            unit_id = unit_id_by_code.get(str(position["department_code"]))
            current_permissions = set(_strings(position.get("permissions")))
            permission_ceiling = ceiling_for(unit_id, "permission_ceiling") if unit_id else None
            if level < 10 and permission_ceiling is not None:
                current_permissions.intersection_update(permission_ceiling)
                direct_allow_ceiling.update(permission_ceiling)
            else:
                has_unrestricted_department = True
            position_permissions.update(current_permissions)
            policy = position_policies.get(str(position["id"]))
            defaults = (
                _strings(policy.get("navigation_default"))
                if policy and policy.get("navigation_default_enabled")
                else _strings(position.get("navigation_defaults"))
            )
            nav_ceiling = ceiling_for(unit_id, "navigation_ceiling") if unit_id else None
            if level < 10 and nav_ceiling is not None:
                defaults = [module for module in defaults if module in nav_ceiling]
            nav_modules.update(defaults)
            identity_rows.append(
                {
                    "position_code": position["position_code"],
                    "name": position["name"],
                    "role_level": int(position["role_level"]),
                    "appointment_type": identity["appointment_type"],
                }
            )
        effective = position_permissions | role_permissions_by_user.get(
            str(member["user_id"]), set()
        )
        direct = permission_overrides.get(str(member["user_id"]), {})
        direct_allow = set(_strings(direct.get("allow_keys")))
        if level < 10 and not has_unrestricted_department and direct_allow_ceiling:
            direct_allow.intersection_update(direct_allow_ceiling)
        effective.update(direct_allow)
        effective.difference_update(_strings(direct.get("deny_keys")))
        if not nav_modules:
            nav_modules.update(NAVIGATION_IDS)
        nav_modules = {
            module
            for module in nav_modules
            if module in NAVIGATION_IDS and _nav_entitled(module, effective, level=level)
        }
        nav_override = navigation_overrides.get(str(member["user_id"]), {})
        nav_modules.update(
            module
            for module in _strings(nav_override.get("allow_modules"))
            if module in NAVIGATION_IDS and _nav_entitled(module, effective, level=level)
        )
        nav_modules.difference_update(_strings(nav_override.get("deny_modules")))
        return (
            effective,
            [item["id"] for item in NAVIGATION_CATALOG if item["id"] in nav_modules],
            identity_rows,
        )

    user_rows: list[dict[str, object]] = []
    memberships_out: list[dict[str, object]] = []
    for member in memberships:
        effective, allowed_nav, identities = authority_for(member)
        user_id = str(member["user_id"])
        role_names = list(
            dict.fromkeys(
                position_by_code[str(identity["position_code"])]["role_name"]
                for identity in identities
            )
        )
        primary_code = next(
            (
                str(identity["position_code"])
                for identity in identities
                if identity["appointment_type"] == "primary"
            ),
            member.get("position_code"),
        )
        primary_position = position_by_code.get(str(primary_code)) if primary_code else None
        unit = (
            unit_by_code.get(str(primary_position["department_code"])) if primary_position else None
        )
        override = permission_overrides.get(user_id, {})
        nav_override = navigation_overrides.get(user_id, {})
        user_rows.append(
            {
                "id": user_id,
                "username": member["username"],
                "display_name": member["display_name"],
                "active": bool(member["user_active"] and member["membership_active"]),
                "role_level": int(member["role_level"]),
                "topology_level": int(member["topology_level"]),
                "topology_title": member["topology_title"],
                "created_at": _iso(member["created_at"]),
                "role_names": role_names,
                "roles": [{"role_name": name} for name in role_names],
                "identities": identities,
                "effective_permissions": sorted(effective),
                "permissions": sorted(effective),
                "allowed_nav": allowed_nav,
                "permission_overrides": {
                    "allow": _strings(override.get("allow_keys")),
                    "deny": _strings(override.get("deny_keys")),
                },
                "nav_overrides": {
                    "allow": _strings(nav_override.get("allow_modules")),
                    "deny": _strings(nav_override.get("deny_modules")),
                },
                "navigation_policy": {
                    "effective_modules": allowed_nav,
                    "permission_modules": [
                        item["id"]
                        for item in NAVIGATION_CATALOG
                        if _nav_entitled(
                            str(item["id"]), effective, level=int(member["role_level"])
                        )
                    ],
                    "source": "position",
                },
            }
        )
        memberships_out.append(
            {
                "id": f"{user_id}:{primary_code or 'unassigned'}",
                "user_id": user_id,
                "username": member["username"],
                "display_name": member["display_name"],
                "org_unit_id": str(unit["id"]) if unit else None,
                "position_id": str(primary_position["id"]) if primary_position else None,
                "position_code": primary_code,
                "position_name": primary_position["name"] if primary_position else None,
                "role_name": primary_position["role_name"] if primary_position else None,
                "role_names": role_names,
                "created_at": _iso(member["membership_created_at"]),
            }
        )

    units_out: list[dict[str, object]] = []
    user_by_id = {str(row["id"]): row for row in user_rows}
    for unit in units:
        policy = policies.get(str(unit["id"]), {})
        parent = (
            unit_by_code.get(str(unit["parent_unit_code"]))
            if unit.get("parent_unit_code")
            else None
        )
        manager = (
            user_by_id.get(str(unit["manager_user_id"])) if unit.get("manager_user_id") else None
        )
        units_out.append(
            {
                "id": str(unit["id"]),
                "unit_code": unit["unit_code"],
                "unit_name": unit["name"],
                "unit_name_en": unit["name_en"],
                "description": unit["description"],
                "unit_type": unit["unit_type"],
                "parent_id": str(parent["id"]) if parent else None,
                "active": bool(unit["active"]),
                "manager_user_id": str(unit["manager_user_id"])
                if unit.get("manager_user_id")
                else None,
                "manager_name": manager["display_name"] if manager else None,
                "permission_ceiling": _strings(policy.get("permission_ceiling")),
                "permission_ceiling_enabled": bool(policy.get("permission_ceiling_enabled")),
                "nav_ceiling": _strings(policy.get("navigation_ceiling")),
                "nav_ceiling_enabled": bool(policy.get("navigation_ceiling_enabled")),
                "effective_nav_ceiling": _strings(policy.get("navigation_ceiling"))
                if policy.get("navigation_ceiling_enabled")
                else [item["id"] for item in NAVIGATION_CATALOG],
                "managed_by_template": not str(unit["unit_code"]).startswith("custom-"),
                "created_at": _iso(unit["created_at"]),
            }
        )
    positions_out: list[dict[str, object]] = []
    for position in positions:
        policy = position_policies.get(str(position["id"]), {})
        unit = unit_by_code.get(str(position["department_code"]))
        defaults = (
            _strings(policy.get("navigation_default"))
            if policy.get("navigation_default_enabled")
            else _strings(position.get("navigation_defaults"))
        )
        positions_out.append(
            {
                "id": str(position["id"]),
                "position_code": position["position_code"],
                "position_name": position["name"],
                "position_name_en": position["name_en"],
                "description": "",
                "org_unit_id": str(unit["id"]) if unit else None,
                "role_id": position["role_name"],
                "role_name": position["role_name"],
                "level": int(position["role_level"]),
                "is_manager": bool(position["is_manager"]),
                "permissions": _strings(position["permissions"]),
                "active": bool(position["active"]),
                "nav_default": defaults,
                "nav_default_enabled": bool(policy.get("navigation_default_enabled")),
                "effective_nav_default": defaults,
                "nav_default_source": "manual"
                if policy.get("navigation_default_enabled")
                else "template",
                "managed_by_template": not str(position["position_code"]).startswith("custom-"),
                "created_at": _iso(position["created_at"]),
            }
        )
    return {
        "units": units_out,
        "positions": positions_out,
        "users": user_rows,
        "memberships": memberships_out,
    }


def _roles(projection: dict[str, object]) -> list[dict[str, object]]:
    positions = projection["positions"]
    users = projection["users"]
    by_name: dict[str, dict[str, object]] = {}
    for position in positions:
        name = str(position["role_name"])
        role = by_name.setdefault(
            name, {"id": name, "role_name": name, "level": 1, "permissions": set()}
        )
        role["level"] = max(int(role["level"]), int(position["level"]))
        role["permissions"].update(position["permissions"])
    for role in by_name.values():
        role["permission_count"] = len(role["permissions"])
        role["permissions"] = sorted(role["permissions"])
        role["user_count"] = sum(1 for user in users if role["role_name"] in user["role_names"])
    return sorted(by_name.values(), key=lambda row: (-int(row["level"]), str(row["role_name"])))


def _permission_catalogue() -> list[dict[str, object]]:
    labels = {key: key.replace(".", " · ").replace("_", " ") for key in BLUEPRINT_PERMISSION_KEYS}
    return [
        {"key": key, "label": labels[key], "group": key.split(".", 1)[0]}
        for key in sorted(BLUEPRINT_PERMISSION_KEYS)
    ]


def organization_structure(actor: ActorContext) -> dict[str, object]:
    _require(
        actor,
        "permissions.topology.read",
        "users.manage",
        "permissions.topology.manage",
        "settings.manage",
    )
    with tenant_session(actor.tenant_id) as session:
        projection = _projection(_snapshot(session))
    template = get_template_summary(actor.industry_template_key) or {
        "key": actor.industry_template_key,
        "name": actor.tenant_name,
        "revision": "—",
    }
    return {
        "template": {**template, "version": template.get("revision")},
        "units": projection["units"],
        "positions": projection["positions"],
        "memberships": projection["memberships"],
        "summary": {
            "departments": sum(
                1
                for unit in projection["units"]
                if unit["unit_type"] != "company" and unit["active"]
            ),
            "positions": sum(1 for position in projection["positions"] if position["active"]),
            "assigned_users": len(
                {row["user_id"] for row in projection["memberships"] if row["position_id"]}
            ),
            "unassigned_users": sum(
                1
                for row in projection["users"]
                if not any(
                    member["user_id"] == row["id"] and member["position_id"]
                    for member in projection["memberships"]
                )
            ),
        },
        "navigation_catalog": list(NAVIGATION_CATALOG),
    }


def users_payload(actor: ActorContext) -> dict[str, object]:
    _require(
        actor,
        "permissions.topology.read",
        "users.manage",
        "permissions.topology.manage",
        "settings.manage",
    )
    with tenant_session(actor.tenant_id) as session:
        projection = _projection(_snapshot(session))
    return {"users": projection["users"], "roles": _roles(projection)}


def topology_payload(actor: ActorContext) -> dict[str, object]:
    _require(
        actor,
        "permissions.topology.read",
        "users.manage",
        "permissions.topology.manage",
        "settings.manage",
    )
    with tenant_session(actor.tenant_id) as session:
        projection = _projection(_snapshot(session))
    can_manage_org = _can_manage_organization(actor)
    can_manage_permissions = _can_manage_permissions(actor)
    return {
        "scope": "current_tenant_only",
        "users": projection["users"],
        "roles": _roles(projection),
        "permissions": _permission_catalogue(),
        "delegations": [],
        "protected_permissions": ["settings.manage", "users.manage", "permissions.topology.manage"],
        "actor": {
            "id": str(actor.user_id),
            "can_manage": can_manage_org or can_manage_permissions,
            "can_edit_organization": can_manage_org,
            "can_edit_permissions": can_manage_permissions,
            "effective_permissions": sorted(actor.permissions),
            "navigation_manageable_modules": [item["id"] for item in NAVIGATION_CATALOG]
            if can_manage_permissions
            else [],
        },
        "summary": {
            "users": len(projection["users"]),
            "roles": len(_roles(projection)),
            "delegations": 0,
        },
    }


def templates_payload(actor: ActorContext) -> dict[str, object]:
    return {
        "templates": list_template_summaries(),
        "current_template": get_template_summary(actor.industry_template_key),
        "can_apply": _permission(actor, "settings.manage"),
    }


def _preview_token(
    actor: ActorContext, template: dict[str, object], projection: dict[str, object]
) -> str:
    material = ":".join(
        (
            str(actor.tenant_id),
            str(actor.industry_template_key),
            str(template["key"]),
            str(template.get("revision")),
            str(len(projection["units"])),
            str(len(projection["positions"])),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def template_preview(actor: ActorContext, template_key: str) -> dict[str, object]:
    detail = _template_blueprint(template_key)
    blueprint = detail["blueprint"]
    with tenant_session(actor.tenant_id) as session:
        projection = _projection(_snapshot(session))
    existing_units = {row["unit_code"] for row in projection["units"]}
    existing_positions = {row["position_code"] for row in projection["positions"]}
    departments = list(blueprint.get("departments") or [])
    positions = list(blueprint.get("positions") or [])
    return {
        "template": {
            key: detail[key] for key in ("key", "name", "description", "schema_version", "revision")
        },
        "preview_token": _preview_token(actor, detail, projection),
        "can_apply": _permission(actor, "settings.manage"),
        "summary": {
            "departments_create": sum(
                1 for item in departments if item.get("code") not in existing_units
            ),
            "departments_sync": sum(
                1 for item in departments if item.get("code") in existing_units
            ),
            "positions_create": sum(
                1 for item in positions if item.get("code") not in existing_positions
            ),
            "positions_sync": sum(
                1 for item in positions if item.get("code") in existing_positions
            ),
            "departments_archive": 0,
            "positions_archive": 0,
            "roles_create": 0,
            "roles_reuse": len({str(item.get("role_name")) for item in positions}),
        },
        "safety": {"mode": "merge", "archives": False, "preserves_custom_data": True},
    }


def _unit(session: Session, unit_id: object) -> dict[str, object]:
    unit = (
        session.execute(
            text("""
        SELECT id, unit_code, name, unit_type, parent_unit_code, active
        FROM iam.organizational_units WHERE id = :id
    """),
            {"id": _uuid(unit_id, label="organization unit id")},
        )
        .mappings()
        .one_or_none()
    )
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization unit not found"
        )
    return dict(unit)


def _position(session: Session, position_id: object) -> dict[str, object]:
    position = (
        session.execute(
            text("""
        SELECT id, position_code, department_code, name, role_name, role_level,
               is_manager, permissions, navigation_defaults, active
        FROM iam.position_profiles WHERE id = :id
    """),
            {"id": _uuid(position_id, label="position id")},
        )
        .mappings()
        .one_or_none()
    )
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return dict(position)


def _manager(session: Session, user_id: object | None) -> UUID | None:
    if user_id in (None, "", 0, "0"):
        return None
    result = _uuid(user_id, label="manager user id")
    exists = session.execute(
        text("SELECT 1 FROM iam.memberships WHERE user_id = :user_id AND active"),
        {"user_id": result},
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Manager must be an active tenant member",
        )
    return result


def _role_source(session: Session, role_id: object | None) -> tuple[str, list[str]]:
    if role_id in (None, ""):
        return "自訂角色", []
    role_name = str(role_id).strip()
    source = (
        session.execute(
            text("""
        SELECT role_name, permissions FROM iam.position_profiles
        WHERE role_name = :role_name AND active
        ORDER BY role_level DESC, position_code LIMIT 1
    """),
            {"role_name": role_name},
        )
        .mappings()
        .one_or_none()
    )
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Selected role is unavailable"
        )
    return str(source["role_name"]), _strings(source["permissions"])


def create_department(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "users.manage", "settings.manage")
    name = str(payload.get("unit_name") or "").strip()
    unit_type = str(payload.get("unit_type") or "department").strip()
    if not name or unit_type not in VALID_DEPARTMENT_TYPES - {"company"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Valid department name and type are required",
        )
    with tenant_session(actor.tenant_id) as session:
        parent = _unit(session, payload.get("parent_id"))
        if not parent["active"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Parent organization unit is inactive",
            )
        unit_code = str(payload.get("unit_code") or "").strip().lower() or _slug(
            name, prefix="custom"
        )
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,79}", unit_code):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid organization unit code",
            )
        unit_id = uuid4()
        session.execute(
            text("""
            INSERT INTO iam.organizational_units(id, tenant_id, template_key, unit_code, name, description, unit_type, parent_unit_code)
            VALUES (:id, :tenant_id, :template_key, :unit_code, :name, :description, :unit_type, :parent_unit_code)
        """),
            {
                "id": unit_id,
                "tenant_id": actor.tenant_id,
                "template_key": actor.industry_template_key,
                "unit_code": unit_code,
                "name": name,
                "description": str(payload.get("description") or "").strip(),
                "unit_type": unit_type,
                "parent_unit_code": parent["unit_code"],
            },
        )
        _audit(
            session,
            actor,
            "organization.department_created",
            {"unit_id": str(unit_id), "unit_code": unit_code},
        )
    return {"ok": True, "id": str(unit_id), "unit_code": unit_code}


def update_department(
    actor: ActorContext, unit_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "users.manage", "settings.manage")
    with tenant_session(actor.tenant_id) as session:
        unit = _unit(session, unit_id)
        if unit["unit_type"] == "company":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Company root cannot be edited here"
            )
        parent = (
            _unit(session, payload.get("parent_id"))
            if payload.get("parent_id") not in (None, "", 0, "0")
            else None
        )
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A parent organization unit is required",
            )
        if str(parent["id"]) == str(unit["id"]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An organization unit cannot be its own parent",
            )
        cursor = parent
        seen: set[str] = set()
        while cursor and str(cursor["id"]) not in seen:
            if str(cursor["id"]) == str(unit["id"]):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Organization hierarchy cycle is not allowed",
                )
            seen.add(str(cursor["id"]))
            parent_code = cursor.get("parent_unit_code")
            cursor = (
                dict(
                    session.execute(
                        text("""
                            SELECT id, unit_code, name, unit_type, parent_unit_code, active
                            FROM iam.organizational_units WHERE unit_code = :unit_code
                        """),
                        {"unit_code": parent_code},
                    )
                    .mappings()
                    .one_or_none()
                )
                if parent_code
                else None
            )
        name = str(payload.get("unit_name") or unit["name"]).strip()
        unit_type = str(payload.get("unit_type") or unit["unit_type"]).strip()
        if not name or unit_type not in VALID_DEPARTMENT_TYPES - {"company"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Valid department name and type are required",
            )
        session.execute(
            text("""
            UPDATE iam.organizational_units
            SET name = :name, description = :description, unit_type = :unit_type,
                parent_unit_code = :parent_unit_code, manager_user_id = :manager_user_id
            WHERE id = :id
        """),
            {
                "id": unit["id"],
                "name": name,
                "description": str(payload.get("description") or "").strip(),
                "unit_type": unit_type,
                "parent_unit_code": parent["unit_code"],
                "manager_user_id": _manager(session, payload.get("manager_user_id")),
            },
        )
        _audit(session, actor, "organization.department_updated", {"unit_id": str(unit["id"])})
    return {"ok": True, "id": str(unit["id"])}


def archive_department(actor: ActorContext, unit_id: str) -> dict[str, object]:
    _require(actor, "users.manage", "settings.manage")
    with tenant_session(actor.tenant_id) as session:
        unit = _unit(session, unit_id)
        if unit["unit_type"] == "company":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Company root cannot be archived"
            )
        blockers = (
            session.execute(
                text("""
            SELECT (SELECT COUNT(*) FROM iam.organizational_units WHERE parent_unit_code = :code AND active) AS children,
                   (SELECT COUNT(*) FROM iam.position_profiles WHERE department_code = :code AND active) AS positions
        """),
                {"code": unit["unit_code"]},
            )
            .mappings()
            .one()
        )
        if int(blockers["children"]) or int(blockers["positions"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Move child departments and positions before archiving this department",
            )
        session.execute(
            text("UPDATE iam.organizational_units SET active = false WHERE id = :id"),
            {"id": unit["id"]},
        )
        _audit(session, actor, "organization.department_archived", {"unit_id": str(unit["id"])})
    return {"ok": True, "id": str(unit["id"]), "active": False}


def set_department_permissions(
    actor: ActorContext, unit_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "users.manage", "permissions.topology.manage", "settings.manage")
    permissions = _validated(
        payload.get("permissions"), BLUEPRINT_PERMISSION_KEYS, label="permission"
    )
    with tenant_session(actor.tenant_id) as session:
        unit = _unit(session, unit_id)
        session.execute(
            text("""
            INSERT INTO iam.department_access_policies(tenant_id, org_unit_id, permission_ceiling_enabled, permission_ceiling)
            VALUES (:tenant_id, :unit_id, :enabled, CAST(:permissions AS jsonb))
            ON CONFLICT (tenant_id, org_unit_id) DO UPDATE SET permission_ceiling_enabled = EXCLUDED.permission_ceiling_enabled, permission_ceiling = EXCLUDED.permission_ceiling
        """),
            {
                "tenant_id": actor.tenant_id,
                "unit_id": unit["id"],
                "enabled": bool(payload.get("enabled")),
                "permissions": json.dumps(permissions),
            },
        )
        _audit(
            session,
            actor,
            "organization.department_permission_ceiling_set",
            {
                "unit_id": str(unit["id"]),
                "enabled": bool(payload.get("enabled")),
                "permissions": permissions,
            },
        )
    return {"ok": True}


def set_department_navigation(
    actor: ActorContext, unit_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "users.manage", "permissions.topology.manage", "settings.manage")
    modules = _validated(payload.get("modules"), NAVIGATION_IDS, label="navigation module")
    with tenant_session(actor.tenant_id) as session:
        unit = _unit(session, unit_id)
        session.execute(
            text("""
            INSERT INTO iam.department_access_policies(tenant_id, org_unit_id, navigation_ceiling_enabled, navigation_ceiling)
            VALUES (:tenant_id, :unit_id, :enabled, CAST(:modules AS jsonb))
            ON CONFLICT (tenant_id, org_unit_id) DO UPDATE SET navigation_ceiling_enabled = EXCLUDED.navigation_ceiling_enabled, navigation_ceiling = EXCLUDED.navigation_ceiling
        """),
            {
                "tenant_id": actor.tenant_id,
                "unit_id": unit["id"],
                "enabled": bool(payload.get("enabled")),
                "modules": json.dumps(modules),
            },
        )
        _audit(
            session,
            actor,
            "organization.department_navigation_ceiling_set",
            {
                "unit_id": str(unit["id"]),
                "enabled": bool(payload.get("enabled")),
                "modules": modules,
            },
        )
    return {"ok": True}


def create_position(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "users.manage", "settings.manage")
    name = str(payload.get("position_name") or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Position name is required"
        )
    level = int(payload.get("level") or 1)
    if not 1 <= level <= 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Position level must be between 1 and 10",
        )
    with tenant_session(actor.tenant_id) as session:
        unit = _unit(session, payload.get("org_unit_id"))
        if unit["unit_type"] == "company" or not unit["active"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An active non-company department is required",
            )
        role_name, permissions = _role_source(session, payload.get("role_id"))
        position_code = str(payload.get("position_code") or "").strip().lower() or _slug(
            name, prefix="custom"
        )
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,79}", position_code):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid position code"
            )
        position_id = uuid4()
        session.execute(
            text("""
            INSERT INTO iam.position_profiles(id, tenant_id, template_key, position_code, department_code, name, role_name, role_level, is_manager, permissions, navigation_defaults)
            VALUES (:id, :tenant_id, :template_key, :position_code, :department_code, :name, :role_name, :level, :is_manager, CAST(:permissions AS jsonb), '[]'::jsonb)
        """),
            {
                "id": position_id,
                "tenant_id": actor.tenant_id,
                "template_key": actor.industry_template_key,
                "position_code": position_code,
                "department_code": unit["unit_code"],
                "name": name,
                "role_name": role_name,
                "level": level,
                "is_manager": bool(payload.get("is_manager")),
                "permissions": json.dumps(permissions),
            },
        )
        _audit(
            session,
            actor,
            "organization.position_created",
            {"position_id": str(position_id), "position_code": position_code},
        )
    return {"ok": True, "id": str(position_id), "position_code": position_code}


def update_position(
    actor: ActorContext, position_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "users.manage", "settings.manage")
    with tenant_session(actor.tenant_id) as session:
        position = _position(session, position_id)
        unit = _unit(session, payload.get("org_unit_id"))
        if unit["unit_type"] == "company" or not unit["active"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An active non-company department is required",
            )
        level = int(payload.get("level") or position["role_level"])
        if not 1 <= level <= 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Position level must be between 1 and 10",
            )
        role_name, permissions = (
            _role_source(session, payload.get("role_id"))
            if "role_id" in payload
            else (str(position["role_name"]), _strings(position["permissions"]))
        )
        name = str(payload.get("position_name") or position["name"]).strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Position name is required"
            )
        session.execute(
            text("""
            UPDATE iam.position_profiles
            SET department_code = :department_code, name = :name, role_name = :role_name,
                role_level = :level, is_manager = :is_manager, permissions = CAST(:permissions AS jsonb)
            WHERE id = :id
        """),
            {
                "id": position["id"],
                "department_code": unit["unit_code"],
                "name": name,
                "role_name": role_name,
                "level": level,
                "is_manager": bool(payload.get("is_manager")),
                "permissions": json.dumps(permissions),
            },
        )
        _audit(
            session, actor, "organization.position_updated", {"position_id": str(position["id"])}
        )
    return {"ok": True, "id": str(position["id"])}


def archive_position(actor: ActorContext, position_id: str) -> dict[str, object]:
    _require(actor, "users.manage", "settings.manage")
    with tenant_session(actor.tenant_id) as session:
        position = _position(session, position_id)
        assigned = session.execute(
            text(
                "SELECT COUNT(*) FROM iam.membership_positions WHERE position_code = :position_code AND active"
            ),
            {"position_code": position["position_code"]},
        ).scalar_one()
        if int(assigned):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Move members before archiving this position",
            )
        session.execute(
            text("UPDATE iam.position_profiles SET active = false WHERE id = :id"),
            {"id": position["id"]},
        )
        _audit(
            session, actor, "organization.position_archived", {"position_id": str(position["id"])}
        )
    return {"ok": True, "id": str(position["id"]), "active": False}


def set_position_navigation(
    actor: ActorContext, position_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "users.manage", "permissions.topology.manage", "settings.manage")
    modules = _validated(payload.get("modules"), NAVIGATION_IDS, label="navigation module")
    with tenant_session(actor.tenant_id) as session:
        position = _position(session, position_id)
        session.execute(
            text("""
            INSERT INTO iam.position_navigation_policies(tenant_id, position_id, navigation_default_enabled, navigation_default)
            VALUES (:tenant_id, :position_id, :enabled, CAST(:modules AS jsonb))
            ON CONFLICT (tenant_id, position_id) DO UPDATE SET navigation_default_enabled = EXCLUDED.navigation_default_enabled, navigation_default = EXCLUDED.navigation_default
        """),
            {
                "tenant_id": actor.tenant_id,
                "position_id": position["id"],
                "enabled": bool(payload.get("enabled")),
                "modules": json.dumps(modules),
            },
        )
        _audit(
            session,
            actor,
            "organization.position_navigation_set",
            {
                "position_id": str(position["id"]),
                "enabled": bool(payload.get("enabled")),
                "modules": modules,
            },
        )
    return {"ok": True}


def _member(session: Session, user_id: str) -> dict[str, object]:
    member = (
        session.execute(
            text("""
        SELECT m.user_id, m.role_level, m.topology_level, m.topology_title, u.username
        FROM iam.memberships AS m JOIN iam.users AS u ON u.id = m.user_id
        WHERE m.user_id = :user_id AND m.active AND u.active
    """),
            {"user_id": _uuid(user_id, label="user id")},
        )
        .mappings()
        .one_or_none()
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Active tenant member not found"
        )
    return dict(member)


def assign_user_position(
    actor: ActorContext, user_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "users.manage", "settings.manage")
    code = str(payload.get("position_code") or "").strip()
    if not code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Position code is required"
        )
    with tenant_session(actor.tenant_id) as session:
        member = _member(session, user_id)
        target = (
            session.execute(
                text("""
            SELECT position_code, role_level FROM iam.position_profiles
            WHERE position_code = :position_code AND active
        """),
                {"position_code": code},
            )
            .mappings()
            .one_or_none()
        )
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Target position is unavailable",
            )
        session.execute(
            text("""
            UPDATE iam.membership_positions SET active = false
            WHERE user_id = :user_id AND appointment_type = 'primary' AND active
        """),
            {"user_id": member["user_id"]},
        )
        session.execute(
            text("""
            INSERT INTO iam.membership_positions(tenant_id, user_id, position_code, appointment_type, active)
            VALUES (:tenant_id, :user_id, :position_code, 'primary', true)
            ON CONFLICT (tenant_id, user_id, position_code) DO UPDATE SET appointment_type = 'primary', active = true
        """),
            {"tenant_id": actor.tenant_id, "user_id": member["user_id"], "position_code": code},
        )
        max_level = session.execute(
            text("""
            SELECT COALESCE(MAX(pp.role_level), 1) FROM iam.membership_positions AS mp
            JOIN iam.position_profiles AS pp ON pp.tenant_id = mp.tenant_id AND pp.position_code = mp.position_code
            WHERE mp.user_id = :user_id AND mp.active AND pp.active
        """),
            {"user_id": member["user_id"]},
        ).scalar_one()
        session.execute(
            text("""
            UPDATE iam.memberships SET position_code = :position_code, role_level = :level, topology_level = GREATEST(topology_level, :level)
            WHERE user_id = :user_id
        """),
            {"position_code": code, "level": int(max_level), "user_id": member["user_id"]},
        )
        _audit(
            session,
            actor,
            "organization.user_position_assigned",
            {"user_id": str(member["user_id"]), "position_code": code},
        )
    return {"ok": True, "user_id": str(member["user_id"]), "position_code": code}


def set_user_permissions(
    actor: ActorContext, user_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "users.manage", "permissions.topology.manage", "settings.manage")
    allow = _validated(payload.get("allow"), BLUEPRINT_PERMISSION_KEYS, label="permission")
    deny = _validated(payload.get("deny"), BLUEPRINT_PERMISSION_KEYS, label="permission")
    allow = [key for key in allow if key not in set(deny)]
    with tenant_session(actor.tenant_id) as session:
        member = _member(session, user_id)
        session.execute(
            text("""
            INSERT INTO iam.membership_permission_overrides(tenant_id, user_id, allow_keys, deny_keys)
            VALUES (:tenant_id, :user_id, CAST(:allow AS jsonb), CAST(:deny AS jsonb))
            ON CONFLICT (tenant_id, user_id) DO UPDATE SET allow_keys = EXCLUDED.allow_keys, deny_keys = EXCLUDED.deny_keys
        """),
            {
                "tenant_id": actor.tenant_id,
                "user_id": member["user_id"],
                "allow": json.dumps(allow),
                "deny": json.dumps(deny),
            },
        )
        _audit(
            session,
            actor,
            "organization.user_permission_overrides_set",
            {"user_id": str(member["user_id"]), "allow": allow, "deny": deny},
        )
    return {"ok": True}


def set_user_navigation(
    actor: ActorContext, user_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "users.manage", "permissions.topology.manage", "settings.manage")
    allow = _validated(payload.get("allow"), NAVIGATION_IDS, label="navigation module")
    deny = _validated(payload.get("deny"), NAVIGATION_IDS, label="navigation module")
    allow = [key for key in allow if key not in set(deny)]
    with tenant_session(actor.tenant_id) as session:
        member = _member(session, user_id)
        session.execute(
            text("""
            INSERT INTO iam.membership_navigation_overrides(tenant_id, user_id, allow_modules, deny_modules)
            VALUES (:tenant_id, :user_id, CAST(:allow AS jsonb), CAST(:deny AS jsonb))
            ON CONFLICT (tenant_id, user_id) DO UPDATE SET allow_modules = EXCLUDED.allow_modules, deny_modules = EXCLUDED.deny_modules
        """),
            {
                "tenant_id": actor.tenant_id,
                "user_id": member["user_id"],
                "allow": json.dumps(allow),
                "deny": json.dumps(deny),
            },
        )
        _audit(
            session,
            actor,
            "organization.user_navigation_overrides_set",
            {"user_id": str(member["user_id"]), "allow": allow, "deny": deny},
        )
    return {"ok": True}


def apply_template(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "settings.manage")
    template_key = str(payload.get("template_key") or "").strip()
    if payload.get("confirm") is not True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Explicit confirmation is required",
        )
    detail = _template_blueprint(template_key)
    blueprint = detail["blueprint"]
    with tenant_session(actor.tenant_id) as session:
        snapshot = _snapshot(session)
        projection = _projection(snapshot)
        if str(payload.get("preview_token") or "") != _preview_token(actor, detail, projection):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Template preview is stale; refresh it before applying",
            )
        existing_units = {str(unit["unit_code"]): unit for unit in snapshot["units"]}
        for department in blueprint.get("departments") or []:
            code = str(department["code"])
            if code in existing_units:
                session.execute(
                    text("""
                    UPDATE iam.organizational_units SET template_key = :template_key, name = :name,
                      name_en = :name_en, description = :description, unit_type = :unit_type,
                      parent_unit_code = :parent_unit_code, active = true
                    WHERE id = :id
                """),
                    {
                        "template_key": template_key,
                        "name": actor.tenant_name if code == "company" else str(department["name"]),
                        "name_en": department.get("name_en"),
                        "description": str(department.get("description") or ""),
                        "unit_type": str(department["type"]),
                        "parent_unit_code": department.get("parent"),
                        "id": existing_units[code]["id"],
                    },
                )
            else:
                session.execute(
                    text("""
                    INSERT INTO iam.organizational_units(id, tenant_id, template_key, unit_code, name, name_en, description, unit_type, parent_unit_code)
                    VALUES (:id, :tenant_id, :template_key, :unit_code, :name, :name_en, :description, :unit_type, :parent_unit_code)
                """),
                    {
                        "id": uuid4(),
                        "tenant_id": actor.tenant_id,
                        "template_key": template_key,
                        "unit_code": code,
                        "name": actor.tenant_name if code == "company" else str(department["name"]),
                        "name_en": department.get("name_en"),
                        "description": str(department.get("description") or ""),
                        "unit_type": str(department["type"]),
                        "parent_unit_code": department.get("parent"),
                    },
                )
        nav_defaults = blueprint_nav_defaults(blueprint)
        existing_positions = {
            str(position["position_code"]): position for position in snapshot["positions"]
        }
        for item in blueprint.get("positions") or []:
            code = str(item["code"])
            values = {
                "template_key": template_key,
                "department_code": str(item["department"]),
                "name": str(item["name"]),
                "name_en": item.get("name_en"),
                "role_name": str(item["role_name"]),
                "role_level": int(item["level"]),
                "is_manager": bool(item["is_manager"]),
                "permissions": json.dumps(item.get("permissions") or []),
                "navigation_defaults": json.dumps(nav_defaults.get(code) or []),
            }
            if code in existing_positions:
                session.execute(
                    text("""
                    UPDATE iam.position_profiles SET template_key = :template_key, department_code = :department_code,
                      name = :name, name_en = :name_en, role_name = :role_name, role_level = :role_level,
                      is_manager = :is_manager, permissions = CAST(:permissions AS jsonb),
                      navigation_defaults = CAST(:navigation_defaults AS jsonb), active = true
                    WHERE id = :id
                """),
                    {**values, "id": existing_positions[code]["id"]},
                )
            else:
                session.execute(
                    text("""
                    INSERT INTO iam.position_profiles(id, tenant_id, template_key, position_code, department_code, name, name_en, role_name, role_level, is_manager, permissions, navigation_defaults)
                    VALUES (:id, :tenant_id, :template_key, :position_code, :department_code, :name, :name_en, :role_name, :role_level, :is_manager, CAST(:permissions AS jsonb), CAST(:navigation_defaults AS jsonb))
                """),
                    {**values, "id": uuid4(), "tenant_id": actor.tenant_id, "position_code": code},
                )
        session.execute(
            text(
                "UPDATE iam.tenants SET industry_template_key = :template_key WHERE id = :tenant_id"
            ),
            {"template_key": template_key, "tenant_id": actor.tenant_id},
        )
        _audit(
            session,
            actor,
            "organization.template_applied",
            {"template_key": template_key, "mode": "merge"},
        )
    return {"ok": True, "template_key": template_key, "mode": "merge"}
