"""Seed derived department policies for every industry and Runtime context.

Revision ID: 20260728_0016
Revises: 20260728_0015
Create Date: 2026-07-28
"""

from __future__ import annotations

import json

from sqlalchemy import text

from alembic import op
from app.templates.industry_blueprints import (
    blueprint_nav_ceilings,
    blueprint_permission_ceilings,
    get_all_blueprints,
)

revision = "20260728_0016"
down_revision = "20260728_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    blueprints = get_all_blueprints()
    for blueprint in blueprints.values():
        bind.execute(
            text(
                """
                UPDATE iam.industry_templates
                SET name = :name, description = :description,
                    schema_version = :schema_version, revision = :revision,
                    blueprint = CAST(:blueprint AS jsonb)
                WHERE template_key = :template_key
                """
            ),
            {
                "template_key": blueprint["key"],
                "name": blueprint["name"],
                "description": blueprint["description"],
                "schema_version": blueprint["schema_version"],
                "revision": blueprint["revision"],
                "blueprint": json.dumps(blueprint, ensure_ascii=False),
            },
        )

    tenants = bind.execute(
        text(
            """
            SELECT id, industry_template_key
            FROM iam.tenants
            WHERE industry_template_key IS NOT NULL
            """
        )
    ).mappings().all()
    for tenant in tenants:
        template_key = str(tenant["industry_template_key"])
        blueprint = blueprints.get(template_key)
        if blueprint is None:
            continue
        tenant_id = tenant["id"]
        bind.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant_id},
        )
        permissions = blueprint_permission_ceilings(blueprint)
        navigation = blueprint_nav_ceilings(blueprint)
        for department in blueprint.get("departments") or []:
            code = str(department["code"])
            # Existing manual policies are company decisions and therefore
            # remain untouched. Missing rows receive the deterministic preset.
            bind.execute(
                text(
                    """
                    INSERT INTO iam.department_access_policies(
                      tenant_id, org_unit_id, permission_ceiling_enabled,
                      permission_ceiling, navigation_ceiling_enabled,
                      navigation_ceiling
                    )
                    SELECT :tenant_id, ou.id, true, CAST(:permissions AS jsonb),
                           true, CAST(:navigation AS jsonb)
                    FROM iam.organizational_units AS ou
                    WHERE ou.tenant_id = :tenant_id AND ou.unit_code = :unit_code
                    ON CONFLICT (tenant_id, org_unit_id) DO NOTHING
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "unit_code": code,
                    "permissions": json.dumps(permissions.get(code) or []),
                    "navigation": json.dumps(navigation.get(code) or []),
                },
            )
        bind.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, event_type, payload)
                VALUES (
                  :tenant_id, 'organization.department_presets_seeded',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "payload": json.dumps(
                    {
                        "template_key": template_key,
                        "revision": blueprint["revision"],
                        "source": "position_subtree_distillation",
                    }
                ),
            },
        )


def downgrade() -> None:
    # Policies may have been edited after seeding; never erase them implicitly.
    pass
