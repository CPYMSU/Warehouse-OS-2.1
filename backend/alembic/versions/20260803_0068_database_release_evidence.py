"""Allow durable database migration release evidence.

Revision ID: 20260803_0068
Revises: 20260803_0067
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0068"
down_revision = "20260803_0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        GRANT UPDATE ON digital_asset.database_migration_history TO warehouse_os;

        COMMENT ON TABLE digital_asset.database_migration_history IS
          'Durable attempted/applied migration evidence used by the deployment release gate.';
        COMMENT ON TABLE digital_asset.database_backups IS
          'Logical backup receipts; ready requires checksum and ephemeral restore evidence.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        REVOKE UPDATE ON digital_asset.database_migration_history FROM warehouse_os;
        """
    )
