"""Keep the research-topic centre separate from the research-technology centre.

Revision ID: 20260728_0015
Revises: 20260728_0014
Create Date: 2026-07-28
"""

from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import text

from alembic import op
from app.templates.industry_blueprints import blueprint_nav_defaults, get_blueprint

revision = "20260728_0015"
down_revision = "20260728_0014"
branch_labels = None
depends_on = None


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def upgrade() -> None:
    bind = op.get_bind()
    blueprint = get_blueprint("research_lab")
    nav_defaults = blueprint_nav_defaults(blueprint)

    # Update the catalogue used when a new company selects or reapplies this
    # preset. Existing tenants are synchronized below.
    bind.execute(
        text(
            """
            UPDATE iam.industry_templates
            SET name = :name, description = :description,
                schema_version = :schema_version, revision = :revision,
                blueprint = CAST(:blueprint AS jsonb)
            WHERE template_key = 'research_lab'
            """
        ),
        {
            "name": blueprint["name"],
            "description": blueprint["description"],
            "schema_version": blueprint["schema_version"],
            "revision": blueprint["revision"],
            "blueprint": _json(blueprint),
        },
    )

    tenant_ids = bind.execute(
        text("SELECT id FROM iam.tenants WHERE industry_template_key = 'research_lab'")
    ).scalars().all()
    for tenant_id in tenant_ids:
        bind.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant_id},
        )
        tenant_name = bind.execute(
            text("SELECT name FROM iam.tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id},
        ).scalar_one()

        for department in blueprint.get("departments") or []:
            code = str(department["code"])
            bind.execute(
                text(
                    """
                    INSERT INTO iam.organizational_units(
                      id, tenant_id, template_key, unit_code, name, name_en,
                      description, unit_type, parent_unit_code, active
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

        for item in blueprint.get("positions") or []:
            code = str(item["code"])
            bind.execute(
                text(
                    """
                    INSERT INTO iam.position_profiles(
                      id, tenant_id, template_key, position_code, department_code,
                      name, name_en, role_name, role_level, is_manager, permissions,
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

        # These pre-preset profiles were already migrated to the new codes in
        # revision 0014. Remove the now-unreferenced rows entirely so no client
        # can mistake them for live root-level positions.
        bind.execute(
            text(
                """
                DELETE FROM iam.position_profiles
                WHERE tenant_id = :tenant_id
                  AND position_code IN ('general_manager', 'research_manager')
                  AND active = false
                  AND NOT EXISTS (
                    SELECT 1 FROM iam.membership_positions mp
                    WHERE mp.tenant_id = :tenant_id
                      AND mp.position_code = iam.position_profiles.position_code
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM iam.memberships m
                    WHERE m.tenant_id = :tenant_id
                      AND m.position_code = iam.position_profiles.position_code
                  )
                """
            ),
            {"tenant_id": tenant_id},
        )
        bind.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, event_type, payload)
                VALUES (
                  :tenant_id, 'organization.research_centres_split',
                  '{"template_key":"research_lab","revision":"2026.07.28.2"}'::jsonb
                )
                """
            ),
            {"tenant_id": tenant_id},
        )


def downgrade() -> None:
    # Do not merge independently editable departments or remove positions that
    # may have acquired appointments after this migration.
    pass
