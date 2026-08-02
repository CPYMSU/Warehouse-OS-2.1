"""Synchronize existing research-lab tenants with the refreshed preset.

Revision ID: 20260728_0014
Revises: 20260728_0013
Create Date: 2026-07-28
"""

from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import text

from alembic import op
from app.templates.industry_blueprints import blueprint_nav_defaults, get_blueprint

revision = "20260728_0014"
down_revision = "20260728_0013"
branch_labels = None
depends_on = None


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def upgrade() -> None:
    bind = op.get_bind()
    blueprint = get_blueprint("research_lab")
    nav_defaults = blueprint_nav_defaults(blueprint)
    tenant_ids = bind.execute(
        text("SELECT id FROM iam.tenants WHERE industry_template_key = 'research_lab'")
    ).scalars().all()

    for tenant_id in tenant_ids:
        bind.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant_id},
        )

        for department in blueprint.get("departments") or []:
            code = str(department["code"])
            tenant_name = bind.execute(
                text("SELECT name FROM iam.tenants WHERE id = :tenant_id"),
                {"tenant_id": tenant_id},
            ).scalar_one()
            bind.execute(
                text(
                    """
                    INSERT INTO iam.organizational_units(
                      id, tenant_id, template_key, unit_code, name, name_en, description,
                      unit_type, parent_unit_code, active
                    ) VALUES (
                      :id, :tenant_id, 'research_lab', :unit_code, :name, :name_en,
                      :description, :unit_type, :parent_unit_code, true
                    )
                    ON CONFLICT (tenant_id, unit_code) DO UPDATE SET
                      template_key = EXCLUDED.template_key,
                      name = EXCLUDED.name,
                      name_en = EXCLUDED.name_en,
                      description = EXCLUDED.description,
                      unit_type = EXCLUDED.unit_type,
                      parent_unit_code = EXCLUDED.parent_unit_code,
                      active = true
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": tenant_id,
                    "unit_code": code,
                    "name": tenant_name if code == "company" else str(department["name"]),
                    "name_en": department.get("name_en"),
                    "description": str(department.get("description") or ""),
                    "unit_type": str(department["type"]),
                    "parent_unit_code": department.get("parent"),
                },
            )

        positions = {str(item["code"]): item for item in blueprint.get("positions") or []}
        # The first research-lab snapshot used generic codes. Move appointments
        # before retiring those profiles so no user identity or multi-position
        # authority is lost.
        for old_code, new_code in (
            ("general_manager", "lab_general_manager"),
            ("research_manager", "research_center_director"),
        ):
            if new_code not in positions:
                continue
            item = positions[new_code]
            bind.execute(
                text(
                    """
                    INSERT INTO iam.position_profiles(
                      id, tenant_id, template_key, position_code, department_code, name,
                      name_en, role_name, role_level, is_manager, permissions,
                      database_access, navigation_defaults, public_entry, case_roles, active
                    ) VALUES (
                      :id, :tenant_id, 'research_lab', :position_code, :department_code,
                      :name, :name_en, :role_name, :role_level, :is_manager,
                      CAST(:permissions AS jsonb), CAST(:database_access AS jsonb),
                      CAST(:navigation_defaults AS jsonb), CAST(:public_entry AS jsonb),
                      CAST(:case_roles AS jsonb), true
                    )
                    ON CONFLICT (tenant_id, position_code) DO NOTHING
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": tenant_id,
                    "position_code": new_code,
                    "department_code": str(item["department"]),
                    "name": str(item["name"]),
                    "name_en": item.get("name_en"),
                    "role_name": str(item["role_name"]),
                    "role_level": int(item["level"]),
                    "is_manager": bool(item["is_manager"]),
                    "permissions": _json(item.get("permissions") or []),
                    "database_access": _json(item.get("database_access") or {}),
                    "navigation_defaults": _json(nav_defaults.get(new_code) or []),
                    "public_entry": _json(item.get("public_entry")),
                    "case_roles": _json(item.get("case_roles") or []),
                },
            )
            bind.execute(
                text(
                    """
                    WITH moved AS (
                      DELETE FROM iam.membership_positions
                      WHERE tenant_id = :tenant_id AND position_code = :old_code
                      RETURNING tenant_id, user_id, appointment_type, active, created_at
                    )
                    INSERT INTO iam.membership_positions(
                      tenant_id, user_id, position_code, appointment_type, active, created_at
                    )
                    SELECT tenant_id, user_id, :new_code, appointment_type, active, created_at
                    FROM moved
                    ON CONFLICT (tenant_id, user_id, position_code) DO UPDATE SET
                      appointment_type = CASE
                        WHEN EXCLUDED.appointment_type = 'primary' THEN 'primary'
                        ELSE iam.membership_positions.appointment_type
                      END,
                      active = iam.membership_positions.active OR EXCLUDED.active
                    """
                ),
                {"tenant_id": tenant_id, "old_code": old_code, "new_code": new_code},
            )
            bind.execute(
                text(
                    """
                    UPDATE iam.memberships SET position_code = :new_code
                    WHERE tenant_id = :tenant_id AND position_code = :old_code
                    """
                ),
                {"tenant_id": tenant_id, "old_code": old_code, "new_code": new_code},
            )
            bind.execute(
                text(
                    """
                    UPDATE iam.position_profiles SET active = false
                    WHERE tenant_id = :tenant_id AND position_code = :old_code
                    """
                ),
                {"tenant_id": tenant_id, "old_code": old_code},
            )

        for code, item in positions.items():
            bind.execute(
                text(
                    """
                    INSERT INTO iam.position_profiles(
                      id, tenant_id, template_key, position_code, department_code, name,
                      name_en, role_name, role_level, is_manager, permissions,
                      database_access, navigation_defaults, public_entry, case_roles, active
                    ) VALUES (
                      :id, :tenant_id, 'research_lab', :position_code, :department_code,
                      :name, :name_en, :role_name, :role_level, :is_manager,
                      CAST(:permissions AS jsonb), CAST(:database_access AS jsonb),
                      CAST(:navigation_defaults AS jsonb), CAST(:public_entry AS jsonb),
                      CAST(:case_roles AS jsonb), true
                    )
                    ON CONFLICT (tenant_id, position_code) DO UPDATE SET
                      template_key = EXCLUDED.template_key,
                      department_code = EXCLUDED.department_code,
                      name = EXCLUDED.name,
                      name_en = EXCLUDED.name_en,
                      role_name = EXCLUDED.role_name,
                      role_level = EXCLUDED.role_level,
                      is_manager = EXCLUDED.is_manager,
                      permissions = EXCLUDED.permissions,
                      database_access = EXCLUDED.database_access,
                      navigation_defaults = EXCLUDED.navigation_defaults,
                      public_entry = EXCLUDED.public_entry,
                      case_roles = EXCLUDED.case_roles,
                      active = true
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": tenant_id,
                    "position_code": code,
                    "department_code": str(item["department"]),
                    "name": str(item["name"]),
                    "name_en": item.get("name_en"),
                    "role_name": str(item["role_name"]),
                    "role_level": int(item["level"]),
                    "is_manager": bool(item["is_manager"]),
                    "permissions": _json(item.get("permissions") or []),
                    "database_access": _json(item.get("database_access") or {}),
                    "navigation_defaults": _json(nav_defaults.get(code) or []),
                    "public_entry": _json(item.get("public_entry")),
                    "case_roles": _json(item.get("case_roles") or []),
                },
            )

        bind.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, event_type, payload)
                VALUES (
                  :tenant_id, 'organization.template_synchronized',
                  '{"template_key":"research_lab","revision":"2026.07.28.2"}'::jsonb
                )
                """
            ),
            {"tenant_id": tenant_id},
        )


def downgrade() -> None:
    # This migration preserves identities while adding missing preset rows.
    # Reversing it would destructively remove positions that may now be in use.
    pass
