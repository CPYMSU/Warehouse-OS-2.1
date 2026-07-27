"""Grant the explicit shipment capability to existing inventory operators.

Revision ID: 20260727_0006
Revises: 20260727_0005
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0006"
down_revision = "20260727_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE iam.position_profiles
        SET permissions = permissions || '["inventory.shipment"]'::jsonb
        WHERE active
          AND permissions ? 'inventory.inbound'
          AND permissions ? 'inventory.outbound'
          AND NOT permissions ? 'inventory.shipment';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE iam.position_profiles
        SET permissions = permissions - 'inventory.shipment'
        WHERE active
          AND permissions ? 'inventory.shipment';
        """
    )
