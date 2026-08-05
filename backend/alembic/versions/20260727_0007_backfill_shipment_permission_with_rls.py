"""Apply the shipment-permission backfill within each tenant RLS context.

Revision ID: 20260727_0007
Revises: 20260727_0006
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0007"
down_revision = "20260727_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE tenant_uuid uuid;
        BEGIN
          FOR tenant_uuid IN SELECT id FROM iam.tenants LOOP
            PERFORM set_config('app.tenant_id', tenant_uuid::text, true);
            UPDATE iam.position_profiles
            SET permissions = permissions || '["inventory.shipment"]'::jsonb
            WHERE active
              AND permissions ? 'inventory.inbound'
              AND permissions ? 'inventory.outbound'
              AND NOT permissions ? 'inventory.shipment';
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # Removing the key can revoke a manually granted entitlement, so downgrade
    # intentionally leaves data intact.  The schema itself is unchanged.
    pass
