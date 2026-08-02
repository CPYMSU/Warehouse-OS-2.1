"""Backfill editable procurement workflow presets for operational tenants.

Revision ID: 20260728_0022
Revises: 20260728_0021
Create Date: 2026-07-28
"""

from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import text

from alembic import op
from app.templates.workflow_blueprints import workflow_blueprints_for_industry

revision = "20260728_0022"
down_revision = "20260728_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    tenants = (
        connection.execute(
            text(
                """
            SELECT id, industry_template_key
            FROM iam.tenants
            WHERE status = 'active'
            ORDER BY created_at, id
            """
            )
        )
        .mappings()
        .all()
    )
    insert_definition = text(
        """
        INSERT INTO workflow.definitions(
          id, tenant_id, workflow_key, name, version, definition, active
        ) VALUES (
          :id, :tenant_id, :workflow_key, :name, 1,
          CAST(:definition AS jsonb), true
        )
        ON CONFLICT (tenant_id, workflow_key, version) DO NOTHING
        """
    )
    for tenant in tenants:
        connection.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant["id"]},
        )
        for definition in workflow_blueprints_for_industry(str(tenant["industry_template_key"])):
            connection.execute(
                insert_definition,
                {
                    "id": uuid4(),
                    "tenant_id": tenant["id"],
                    "workflow_key": definition["workflow_key"],
                    "name": definition["name"],
                    "definition": json.dumps(definition, ensure_ascii=False),
                },
            )


def downgrade() -> None:
    connection = op.get_bind()
    tenant_ids = (
        connection.execute(text("SELECT id FROM iam.tenants ORDER BY created_at, id"))
        .scalars()
        .all()
    )
    for tenant_id in tenant_ids:
        connection.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant_id},
        )
        connection.execute(
            text(
                """
                DELETE FROM workflow.definitions AS definition
                WHERE definition.version = 1
                  AND definition.definition->'source'->>'migration' =
                      'postgresql_data_driven'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM workflow.instances AS instance
                    WHERE instance.tenant_id = definition.tenant_id
                      AND instance.definition_id = definition.id
                  )
                """
            )
        )
