"""Add isolated backup identity evidence and complete workspace occupancy.

Revision ID: 20260803_0070
Revises: 20260803_0069
"""

from alembic import op

revision = "20260803_0070"
down_revision = "20260803_0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE digital_asset.database_bindings
          ADD COLUMN backup_role_ref text
            CHECK (
              backup_role_ref IS NULL
              OR backup_role_ref ~ '^[a-z][a-z0-9_]{1,62}$'
            );

        UPDATE digital_asset.database_bindings
        SET backup_role_ref = 'whb_' || replace(workspace_id::text, '-', '')
        WHERE provider_key = 'warehouse_postgresql_hdd_data_api';

        ALTER TABLE digital_asset.workspace_usage
          ADD COLUMN data_volume_bytes bigint NOT NULL DEFAULT 0
            CHECK (data_volume_bytes >= 0);

        ALTER TABLE digital_asset.workspace_usage
          DROP COLUMN total_billable_bytes;
        ALTER TABLE digital_asset.workspace_usage
          ADD COLUMN total_billable_bytes bigint GENERATED ALWAYS AS (
            code_bytes + data_object_bytes + database_bytes
            + runtime_bytes + data_volume_bytes
          ) STORED;

        COMMENT ON COLUMN digital_asset.database_bindings.backup_role_ref IS
          'NOLOGIN, BYPASSRLS provider role used only by the trusted backup control plane.';
        COMMENT ON COLUMN digital_asset.workspace_usage.code_bytes IS
          'Logical bytes of custodied source archives for the workspace asset.';
        COMMENT ON COLUMN digital_asset.workspace_usage.runtime_bytes IS
          'All retained Runtime releases, build outputs, virtual environments and dependency caches.';
        COMMENT ON COLUMN digital_asset.workspace_usage.data_volume_bytes IS
          'Customer-created bytes in the persistent DATA volume, excluding the reserved .runtime subtree.';
        COMMENT ON TABLE digital_asset.workspace_usage IS
          'Platform occupancy ledger for source archives, managed data objects, Runtime releases, '
          'persistent DATA, and hosted PostgreSQL.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE digital_asset.workspace_usage
          DROP COLUMN total_billable_bytes;
        ALTER TABLE digital_asset.workspace_usage
          ADD COLUMN total_billable_bytes bigint GENERATED ALWAYS AS (
            code_bytes + data_object_bytes + database_bytes + runtime_bytes
          ) STORED;
        ALTER TABLE digital_asset.workspace_usage
          DROP COLUMN data_volume_bytes;
        ALTER TABLE digital_asset.database_bindings
          DROP COLUMN backup_role_ref;
        """
    )
