from __future__ import annotations

import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import system_session
from app.templates.industry_blueprints import (
    blueprint_nav_ceilings,
    blueprint_nav_defaults,
    blueprint_permission_ceilings,
)
from app.templates.workflow_blueprints import workflow_blueprints_for_industry


def list_template_summaries() -> list[dict[str, object]]:
    with system_session() as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT template_key AS key, name, description, schema_version, revision,
                       jsonb_array_length(blueprint->'departments') AS department_count,
                       jsonb_array_length(blueprint->'positions') AS position_count
                FROM iam.industry_templates
                WHERE active
                ORDER BY template_key
                """
                )
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def get_template_detail(template_key: str) -> dict[str, object] | None:
    with system_session() as session:
        row = (
            session.execute(
                text(
                    """
                SELECT template_key AS key, name, description, schema_version, revision, blueprint
                FROM iam.industry_templates
                WHERE template_key = :template_key AND active
                """
                ),
                {"template_key": template_key},
            )
            .mappings()
            .one_or_none()
        )
    return dict(row) if row is not None else None


def get_template_summary(template_key: str) -> dict[str, object] | None:
    with system_session() as session:
        row = (
            session.execute(
                text(
                    """
                SELECT template_key AS key, name, description, schema_version, revision
                FROM iam.industry_templates
                WHERE template_key = :template_key AND active
                """
                ),
                {"template_key": template_key},
            )
            .mappings()
            .one_or_none()
        )
    return dict(row) if row is not None else None


def provision_tenant_template(
    session: Session,
    *,
    tenant_id: UUID,
    tenant_name: str,
    template_key: str,
) -> dict[str, int | str]:
    """Replace an empty tenant's organization snapshot with one catalogued template."""
    row = (
        session.execute(
            text(
                """
            SELECT template_key, blueprint
            FROM iam.industry_templates
            WHERE template_key = :template_key AND active
            """
            ),
            {"template_key": template_key},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ValueError(f"Unknown active industry template: {template_key}")

    blueprint = row["blueprint"]
    if isinstance(blueprint, str):
        blueprint = json.loads(blueprint)
    if not isinstance(blueprint, dict):
        raise ValueError(f"Invalid blueprint payload for template: {template_key}")

    session.execute(
        text("DELETE FROM iam.position_profiles WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    )
    session.execute(
        text("DELETE FROM iam.organizational_units WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    )

    insert_unit = text(
        """
        INSERT INTO iam.organizational_units(
          id, tenant_id, template_key, unit_code, name, name_en, description, unit_type,
          parent_unit_code
        ) VALUES (
          :id, :tenant_id, :template_key, :unit_code, :name, :name_en, :description,
          :unit_type, :parent_unit_code
        )
        """
    )
    departments = list(blueprint.get("departments") or [])
    for department in departments:
        unit_code = str(department["code"])
        session.execute(
            insert_unit,
            {
                "id": uuid4(),
                "tenant_id": tenant_id,
                "template_key": template_key,
                "unit_code": unit_code,
                "name": tenant_name if unit_code == "company" else str(department["name"]),
                "name_en": department.get("name_en"),
                "description": str(department.get("description") or ""),
                "unit_type": str(department["type"]),
                "parent_unit_code": department.get("parent"),
            },
        )

    navigation_defaults = blueprint_nav_defaults(blueprint)
    insert_position = text(
        """
        INSERT INTO iam.position_profiles(
          id, tenant_id, template_key, position_code, department_code, name, name_en,
          role_name, role_level, is_manager, permissions, database_access,
          navigation_defaults, public_entry, case_roles
        ) VALUES (
          :id, :tenant_id, :template_key, :position_code, :department_code, :name,
          :name_en, :role_name, :role_level, :is_manager, CAST(:permissions AS jsonb),
          CAST(:database_access AS jsonb), CAST(:navigation_defaults AS jsonb),
          CAST(:public_entry AS jsonb), CAST(:case_roles AS jsonb)
        )
        """
    )
    positions = list(blueprint.get("positions") or [])
    for position in positions:
        position_code = str(position["code"])
        session.execute(
            insert_position,
            {
                "id": uuid4(),
                "tenant_id": tenant_id,
                "template_key": template_key,
                "position_code": position_code,
                "department_code": str(position["department"]),
                "name": str(position["name"]),
                "name_en": position.get("name_en"),
                "role_name": str(position["role_name"]),
                "role_level": int(position["level"]),
                "is_manager": bool(position["is_manager"]),
                "permissions": json.dumps(position.get("permissions") or []),
                "database_access": json.dumps(position.get("database_access") or {}),
                "navigation_defaults": json.dumps(navigation_defaults.get(position_code) or []),
                "public_entry": json.dumps(position.get("public_entry")),
                "case_roles": json.dumps(position.get("case_roles") or []),
            },
        )

    permission_ceilings = blueprint_permission_ceilings(blueprint)
    navigation_ceilings = blueprint_nav_ceilings(blueprint)
    session.execute(
        text(
            """
            INSERT INTO iam.department_access_policies(
              tenant_id, org_unit_id, permission_ceiling_enabled,
              permission_ceiling, navigation_ceiling_enabled, navigation_ceiling
            )
            SELECT :tenant_id, ou.id, true, CAST(:permissions AS jsonb),
                   true, CAST(:navigation AS jsonb)
            FROM iam.organizational_units AS ou
            WHERE ou.tenant_id = :tenant_id AND ou.unit_code = :unit_code
            ON CONFLICT (tenant_id, org_unit_id) DO UPDATE SET
              permission_ceiling_enabled = EXCLUDED.permission_ceiling_enabled,
              permission_ceiling = EXCLUDED.permission_ceiling,
              navigation_ceiling_enabled = EXCLUDED.navigation_ceiling_enabled,
              navigation_ceiling = EXCLUDED.navigation_ceiling
            """
        ),
        [
            {
                "tenant_id": tenant_id,
                "unit_code": department["code"],
                "permissions": json.dumps(permission_ceilings.get(str(department["code"])) or []),
                "navigation": json.dumps(navigation_ceilings.get(str(department["code"])) or []),
            }
            for department in departments
        ],
    )

    workflow_count = 0
    for definition in workflow_blueprints_for_industry(template_key):
        inserted = session.execute(
            text(
                """
                INSERT INTO workflow.definitions(
                  id, tenant_id, workflow_key, name, version, definition, active
                ) VALUES (
                  :id, :tenant_id, :workflow_key, :name, 1,
                  CAST(:definition AS jsonb), true
                )
                ON CONFLICT (tenant_id, workflow_key, version) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": tenant_id,
                "workflow_key": definition["workflow_key"],
                "name": definition["name"],
                "definition": json.dumps(definition, ensure_ascii=False),
            },
        ).scalar_one_or_none()
        workflow_count += int(inserted is not None)

    return {
        "template_key": template_key,
        "admin_position_code": str(blueprint["admin_position_code"]),
        "department_count": len(departments),
        "position_count": len(positions),
        "workflow_count": workflow_count,
    }
