"""Add primary and delegated workspace API keys.

Revision ID: 20260801_0040
Revises: 20260801_0039
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0040"
down_revision = "20260801_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE digital_asset.api_credentials
          ADD COLUMN key_kind text NOT NULL DEFAULT 'delegated',
          ADD COLUMN parent_credential_id uuid;

        ALTER TABLE digital_asset.api_credentials
          ADD CONSTRAINT api_credentials_key_kind_check
            CHECK (key_kind IN ('primary', 'delegated')),
          ADD CONSTRAINT api_credentials_parent_fk
            FOREIGN KEY (tenant_id, parent_credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id, id),
          ADD CONSTRAINT api_credentials_primary_parent_check
            CHECK (key_kind <> 'primary' OR parent_credential_id IS NULL),
          ADD CONSTRAINT api_credentials_primary_scopes_check
            CHECK (
              key_kind <> 'primary'
              OR scopes @> ARRAY[
                'workspace:read', 'data:read', 'data:write',
                'deploy:read', 'deploy:write', 'logs:read'
              ]::text[]
            );

        WITH ranked AS (
          SELECT id,
                 row_number() OVER (
                   PARTITION BY tenant_id, workspace_id
                   ORDER BY
                     CASE
                       WHEN expires_at IS NULL OR expires_at > now() THEN 0
                       ELSE 1
                     END,
                     issued_at DESC,
                     id
                 ) AS rank
          FROM digital_asset.api_credentials
          WHERE revoked_at IS NULL
        )
        UPDATE digital_asset.api_credentials AS credential
        SET key_kind = 'primary',
            parent_credential_id = NULL,
            scopes = ARRAY[
              'workspace:read', 'data:read', 'data:write',
              'deploy:read', 'deploy:write', 'logs:read'
            ]::text[]
        FROM ranked
        WHERE ranked.id = credential.id AND ranked.rank = 1;

        UPDATE digital_asset.api_credentials AS delegated
        SET parent_credential_id = primary_key.id
        FROM digital_asset.api_credentials AS primary_key
        WHERE delegated.tenant_id = primary_key.tenant_id
          AND delegated.workspace_id = primary_key.workspace_id
          AND delegated.key_kind = 'delegated'
          AND primary_key.key_kind = 'primary'
          AND primary_key.revoked_at IS NULL;

        CREATE UNIQUE INDEX uq_digital_asset_current_primary_key
          ON digital_asset.api_credentials(tenant_id, workspace_id)
          WHERE key_kind = 'primary' AND revoked_at IS NULL;
        CREATE INDEX idx_digital_asset_delegated_key_parent
          ON digital_asset.api_credentials(tenant_id, parent_credential_id)
          WHERE key_kind = 'delegated';

        COMMENT ON COLUMN digital_asset.api_credentials.key_kind IS
          'primary is the workspace root key with every workspace scope; delegated keys have independently restricted scopes.';
        COMMENT ON COLUMN digital_asset.api_credentials.parent_credential_id IS
          'Primary key current when a delegated key was issued. Rotation does not invalidate delegated keys.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS digital_asset.idx_digital_asset_delegated_key_parent;
        DROP INDEX IF EXISTS digital_asset.uq_digital_asset_current_primary_key;
        ALTER TABLE digital_asset.api_credentials
          DROP CONSTRAINT IF EXISTS api_credentials_primary_scopes_check,
          DROP CONSTRAINT IF EXISTS api_credentials_primary_parent_check,
          DROP CONSTRAINT IF EXISTS api_credentials_parent_fk,
          DROP CONSTRAINT IF EXISTS api_credentials_key_kind_check,
          DROP COLUMN IF EXISTS parent_credential_id,
          DROP COLUMN IF EXISTS key_kind;
        """
    )
