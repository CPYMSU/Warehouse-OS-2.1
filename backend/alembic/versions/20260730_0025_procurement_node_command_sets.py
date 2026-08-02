"""Version procurement workflow nodes with shared command-set bindings.

Revision ID: 20260730_0025
Revises: 20260730_0024
Create Date: 2026-07-30
"""

from __future__ import annotations

import json
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import text

from alembic import op
from app.templates.workflow_blueprints import workflow_blueprints_for_industry

revision = "20260730_0025"
down_revision = "20260730_0024"
branch_labels = None
depends_on = None


def _command_nodes(template_key: str) -> dict[str, dict[str, dict[str, object]]]:
    return {
        str(definition["workflow_key"]): {
            str(node["node_key"]): {
                "actions": deepcopy(node["actions"]),
                "command_binding_schema_version": node[
                    "command_binding_schema_version"
                ],
            }
            for node in definition["nodes"]
        }
        for definition in workflow_blueprints_for_industry(template_key)
    }


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
    for tenant in tenants:
        tenant_id = tenant["id"]
        command_nodes = _command_nodes(str(tenant["industry_template_key"]))
        if not command_nodes:
            continue
        connection.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant_id},
        )
        rows = (
            connection.execute(
                text(
                    """
                    SELECT DISTINCT ON (workflow_key)
                           id, workflow_key, name, version, definition
                    FROM workflow.definitions
                    WHERE tenant_id = :tenant_id
                      AND active
                      AND workflow_key = ANY(:workflow_keys)
                    ORDER BY workflow_key, version DESC
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "workflow_keys": list(command_nodes),
                },
            )
            .mappings()
            .all()
        )
        for row in rows:
            workflow_key = str(row["workflow_key"])
            body = deepcopy(row["definition"] or {})
            nodes = body.get("nodes")
            if not isinstance(nodes, list):
                continue
            mapped_nodes = command_nodes.get(workflow_key) or {}
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                mapped = mapped_nodes.get(str(node.get("node_key") or ""))
                if mapped:
                    node.update(deepcopy(mapped))
            body["revision"] = "2026.07.30.2"
            body["command_binding_schema_version"] = 1
            source = body.get("source")
            if not isinstance(source, dict):
                source = {}
                body["source"] = source
            source["action_mapping_migration"] = revision
            next_version = int(
                connection.execute(
                    text(
                        """
                        SELECT COALESCE(MAX(version), 0) + 1
                        FROM workflow.definitions
                        WHERE tenant_id = :tenant_id AND workflow_key = :workflow_key
                        """
                    ),
                    {"tenant_id": tenant_id, "workflow_key": workflow_key},
                ).scalar_one()
            )
            inserted = connection.execute(
                text(
                    """
                    INSERT INTO workflow.definitions(
                      id, tenant_id, workflow_key, name, version, definition, active
                    ) VALUES (
                      :id, :tenant_id, :workflow_key, :name, :version,
                      CAST(:definition AS jsonb), true
                    )
                    ON CONFLICT (tenant_id, workflow_key, version) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": tenant_id,
                    "workflow_key": workflow_key,
                    "name": row["name"],
                    "version": next_version,
                    "definition": json.dumps(body, ensure_ascii=False),
                },
            ).scalar_one_or_none()
            if inserted is not None:
                connection.execute(
                    text(
                        """
                        UPDATE workflow.definitions
                        SET active = false, updated_at = now()
                        WHERE tenant_id = :tenant_id
                          AND workflow_key = :workflow_key
                          AND id <> :inserted_id
                          AND active
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "workflow_key": workflow_key,
                        "inserted_id": inserted,
                    },
                )


def downgrade() -> None:
    connection = op.get_bind()
    rows = (
        connection.execute(
            text(
                """
                SELECT id, tenant_id, workflow_key, version
                FROM workflow.definitions
                WHERE definition->'source'->>'action_mapping_migration' = :revision
                ORDER BY tenant_id, workflow_key, version DESC
                """
            ),
            {"revision": revision},
        )
        .mappings()
        .all()
    )
    for row in rows:
        connection.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": row["tenant_id"]},
        )
        connection.execute(
            text(
                """
                UPDATE workflow.definitions
                SET active = false, updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": row["id"]},
        )
        connection.execute(
            text(
                """
                UPDATE workflow.definitions
                SET active = true, updated_at = now()
                WHERE id = (
                  SELECT id
                  FROM workflow.definitions
                  WHERE tenant_id = :tenant_id
                    AND workflow_key = :workflow_key
                    AND version < :version
                  ORDER BY version DESC
                  LIMIT 1
                )
                """
            ),
            {
                "tenant_id": row["tenant_id"],
                "workflow_key": row["workflow_key"],
                "version": row["version"],
            },
        )
        connection.execute(
            text(
                """
                DELETE FROM workflow.definitions AS definition
                WHERE definition.id = :id
                  AND NOT EXISTS (
                    SELECT 1
                    FROM workflow.instances AS instance
                    WHERE instance.tenant_id = definition.tenant_id
                      AND instance.definition_id = definition.id
                  )
                """
            ),
            {"id": row["id"]},
        )
