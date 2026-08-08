"""Register the CIVILIZATION company preset in the template catalogue.

Revision ID: 20260808_0088
Revises: 20260808_0087
"""

from __future__ import annotations

import json

from alembic import op
from sqlalchemy import text

from app.templates.industry_blueprints import get_all_blueprints

revision = "20260808_0088"
down_revision = "20260808_0087"
branch_labels = None
depends_on = None
warehouse_scope = "primary_data"


def upgrade() -> None:
    bind = op.get_bind()
    for blueprint in get_all_blueprints().values():
        bind.execute(
            text(
                """
                INSERT INTO iam.industry_templates(
                  template_key, name, description, schema_version,
                  revision, blueprint, active
                ) VALUES (
                  :template_key, :name, :description, :schema_version,
                  :revision, CAST(:blueprint AS jsonb), true
                )
                ON CONFLICT (template_key) DO UPDATE SET
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  schema_version = EXCLUDED.schema_version,
                  revision = EXCLUDED.revision,
                  blueprint = EXCLUDED.blueprint,
                  active = true
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


def downgrade() -> None:
    op.get_bind().execute(
        text(
            """
            DELETE FROM iam.industry_templates AS template
            WHERE template.template_key = 'civilization'
              AND NOT EXISTS (
                SELECT 1 FROM iam.tenants AS tenant
                WHERE tenant.industry_template_key = template.template_key
              )
            """
        )
    )
