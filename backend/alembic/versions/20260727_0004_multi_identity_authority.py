"""Represent concurrent tenant appointments and aggregate their authority.

Revision ID: 20260727_0004
Revises: 20260727_0003
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0004"
down_revision = "20260727_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.membership_positions (
          tenant_id uuid NOT NULL,
          user_id uuid NOT NULL,
          position_code text NOT NULL,
          appointment_type text NOT NULL DEFAULT 'concurrent'
            CHECK (appointment_type IN ('primary', 'concurrent')),
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, user_id, position_code),
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, position_code)
            REFERENCES iam.position_profiles(tenant_id, position_code) ON DELETE RESTRICT
        );
        CREATE UNIQUE INDEX uq_membership_positions_one_primary
          ON iam.membership_positions(tenant_id, user_id)
          WHERE appointment_type = 'primary' AND active;
        CREATE INDEX idx_membership_positions_tenant_user_active
          ON iam.membership_positions(tenant_id, user_id, active, appointment_type);

        INSERT INTO iam.membership_positions(
          tenant_id, user_id, position_code, appointment_type
        )
        SELECT tenant_id, user_id, position_code, 'primary'
        FROM iam.memberships
        WHERE position_code IS NOT NULL
        ON CONFLICT (tenant_id, user_id, position_code) DO NOTHING;

        CREATE TRIGGER trg_membership_positions_updated
          BEFORE UPDATE ON iam.membership_positions
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE iam.membership_positions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.membership_positions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.membership_positions
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        GRANT SELECT, INSERT, UPDATE, DELETE ON iam.membership_positions TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iam.membership_positions;")
