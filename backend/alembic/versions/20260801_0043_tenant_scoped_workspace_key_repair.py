"""Repair workspace key hierarchy inside each tenant RLS context.

Revision ID: 20260801_0043
Revises: 20260801_0042
Create Date: 2026-08-01
"""

from __future__ import annotations

from sqlalchemy import text

from alembic import op

revision = "20260801_0043"
down_revision = "20260801_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tenant_ids = bind.execute(text("SELECT id FROM iam.tenants")).scalars().all()
    for tenant_id in tenant_ids:
        bind.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant_id},
        )
        bind.execute(
            text(
                """
                WITH missing_primary AS (
                  SELECT tenant_id, workspace_id
                  FROM digital_asset.api_credentials
                  WHERE tenant_id = :tenant_id
                  GROUP BY tenant_id, workspace_id
                  HAVING count(*) FILTER (
                    WHERE key_kind = 'primary' AND revoked_at IS NULL
                  ) = 0
                ), ranked AS (
                  SELECT credential.id,
                         row_number() OVER (
                           PARTITION BY
                             credential.tenant_id, credential.workspace_id
                           ORDER BY
                             CASE
                               WHEN credential.expires_at IS NULL
                                 OR credential.expires_at > now() THEN 0
                               ELSE 1
                             END,
                             credential.issued_at DESC,
                             credential.id
                         ) AS rank
                  FROM digital_asset.api_credentials AS credential
                  JOIN missing_primary
                    ON missing_primary.tenant_id = credential.tenant_id
                   AND missing_primary.workspace_id = credential.workspace_id
                  WHERE credential.tenant_id = :tenant_id
                    AND credential.revoked_at IS NULL
                )
                UPDATE digital_asset.api_credentials AS credential
                SET key_kind = 'primary',
                    parent_credential_id = NULL,
                    scopes = ARRAY[
                      'workspace:read', 'data:read', 'data:write',
                      'deploy:read', 'deploy:write', 'logs:read'
                    ]::text[]
                FROM ranked
                WHERE credential.tenant_id = :tenant_id
                  AND ranked.id = credential.id
                  AND ranked.rank = 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        bind.execute(
            text(
                """
                UPDATE digital_asset.api_credentials AS delegated
                SET parent_credential_id = primary_key.id
                FROM digital_asset.api_credentials AS primary_key
                WHERE delegated.tenant_id = :tenant_id
                  AND delegated.tenant_id = primary_key.tenant_id
                  AND delegated.workspace_id = primary_key.workspace_id
                  AND delegated.key_kind = 'delegated'
                  AND delegated.parent_credential_id IS NULL
                  AND primary_key.key_kind = 'primary'
                  AND primary_key.revoked_at IS NULL
                """
            ),
            {"tenant_id": tenant_id},
        )


def downgrade() -> None:
    # Keep the repaired hierarchy; reverting would recreate orphaned keys.
    pass
