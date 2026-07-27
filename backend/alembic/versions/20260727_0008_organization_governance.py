"""Persist organisation policies and person-level governance overrides.

Revision ID: 20260727_0008
Revises: 20260727_0007
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0008"
down_revision = "20260727_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE iam.organizational_units
          ADD COLUMN manager_user_id uuid;

        CREATE TABLE iam.department_access_policies (
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          org_unit_id uuid NOT NULL,
          permission_ceiling_enabled boolean NOT NULL DEFAULT false,
          permission_ceiling jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(permission_ceiling) = 'array'),
          navigation_ceiling_enabled boolean NOT NULL DEFAULT false,
          navigation_ceiling jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(navigation_ceiling) = 'array'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, org_unit_id),
          FOREIGN KEY (tenant_id, org_unit_id)
            REFERENCES iam.organizational_units(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE iam.position_navigation_policies (
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          position_id uuid NOT NULL,
          navigation_default_enabled boolean NOT NULL DEFAULT false,
          navigation_default jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(navigation_default) = 'array'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, position_id),
          FOREIGN KEY (tenant_id, position_id)
            REFERENCES iam.position_profiles(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE iam.membership_permission_overrides (
          tenant_id uuid NOT NULL,
          user_id uuid NOT NULL,
          allow_keys jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(allow_keys) = 'array'),
          deny_keys jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(deny_keys) = 'array'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, user_id),
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE
        );

        CREATE TABLE iam.membership_navigation_overrides (
          tenant_id uuid NOT NULL,
          user_id uuid NOT NULL,
          allow_modules jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(allow_modules) = 'array'),
          deny_modules jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(deny_modules) = 'array'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, user_id),
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE
        );

        CREATE TRIGGER trg_department_access_policies_updated
          BEFORE UPDATE ON iam.department_access_policies
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_position_navigation_policies_updated
          BEFORE UPDATE ON iam.position_navigation_policies
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_membership_permission_overrides_updated
          BEFORE UPDATE ON iam.membership_permission_overrides
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_membership_navigation_overrides_updated
          BEFORE UPDATE ON iam.membership_navigation_overrides
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        GRANT SELECT, INSERT, UPDATE, DELETE ON iam.department_access_policies,
          iam.position_navigation_policies, iam.membership_permission_overrides,
          iam.membership_navigation_overrides TO warehouse_os;

        ALTER TABLE iam.department_access_policies ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.department_access_policies FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.department_access_policies
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE iam.position_navigation_policies ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.position_navigation_policies FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.position_navigation_policies
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE iam.membership_permission_overrides ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.membership_permission_overrides FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.membership_permission_overrides
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE iam.membership_navigation_overrides ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.membership_navigation_overrides FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.membership_navigation_overrides
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS iam.membership_navigation_overrides;
        DROP TABLE IF EXISTS iam.membership_permission_overrides;
        DROP TABLE IF EXISTS iam.position_navigation_policies;
        DROP TABLE IF EXISTS iam.department_access_policies;
        ALTER TABLE iam.organizational_units DROP COLUMN IF EXISTS manager_user_id;
        """
    )
