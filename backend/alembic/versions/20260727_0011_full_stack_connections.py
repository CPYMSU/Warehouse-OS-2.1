"""Add persistence needed by retained client workflows.

Revision ID: 20260727_0011
Revises: 20260727_0010
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0011"
down_revision = "20260727_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS platform;

        ALTER TABLE iam.users
          ADD COLUMN IF NOT EXISTS is_platform_owner boolean NOT NULL DEFAULT false;

        CREATE TABLE iam.user_profiles (
          user_id uuid PRIMARY KEY REFERENCES iam.users(id) ON DELETE CASCADE,
          profile jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(profile) = 'object'),
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER trg_user_profiles_updated
          BEFORE UPDATE ON iam.user_profiles
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE iam.passkeys (
          id uuid PRIMARY KEY,
          user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
          credential_id text NOT NULL UNIQUE,
          name text,
          credential jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(credential) = 'object'),
          transports jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(transports) = 'array'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          last_used_at timestamptz
        );
        CREATE INDEX idx_passkeys_user ON iam.passkeys(user_id, created_at DESC);
        CREATE TRIGGER trg_passkeys_updated
          BEFORE UPDATE ON iam.passkeys
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE iam.passkey_challenges (
          request_id uuid PRIMARY KEY,
          user_id uuid REFERENCES iam.users(id) ON DELETE CASCADE,
          username text,
          challenge text NOT NULL,
          kind text NOT NULL CHECK (kind IN ('login', 'register', 'step_up')),
          purpose text,
          resource jsonb NOT NULL DEFAULT '{}'::jsonb,
          expires_at timestamptz NOT NULL,
          used_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_passkey_challenges_expires
          ON iam.passkey_challenges(expires_at, used_at);

        CREATE TABLE platform.company_signups (
          id uuid PRIMARY KEY,
          requester_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
          source_tenant_id uuid REFERENCES iam.tenants(id) ON DELETE SET NULL,
          company_name text NOT NULL,
          slug text NOT NULL,
          industry_template_key text NOT NULL REFERENCES iam.industry_templates(template_key),
          contact text,
          reason text,
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'approved', 'rejected')),
          note text,
          reviewed_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          approved_tenant_id uuid REFERENCES iam.tenants(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX uq_company_signups_open_slug
          ON platform.company_signups(lower(slug))
          WHERE status = 'pending';
        CREATE TRIGGER trg_company_signups_updated
          BEFORE UPDATE ON platform.company_signups
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE platform.membership_requests (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
          requested_org_unit_code text,
          requested_position_code text,
          requested_role_id text,
          department text,
          contact text,
          reason text,
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'approved', 'rejected')),
          note text,
          reviewed_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, user_id)
        );
        CREATE INDEX idx_membership_requests_tenant_status
          ON platform.membership_requests(tenant_id, status, created_at DESC);
        CREATE TRIGGER trg_membership_requests_updated
          BEFORE UPDATE ON platform.membership_requests
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE platform.runtime_states (
          state_key text PRIMARY KEY,
          state jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(state) = 'object'),
          updated_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER trg_runtime_states_updated
          BEFORE UPDATE ON platform.runtime_states
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE compatibility.blobs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          namespace text NOT NULL,
          entity_key text NOT NULL,
          field_key text,
          file_name text NOT NULL,
          content_type text NOT NULL DEFAULT 'application/octet-stream',
          content bytea NOT NULL,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_compatibility_blobs_entity
          ON compatibility.blobs(tenant_id, namespace, entity_key, created_at DESC);
        ALTER TABLE compatibility.blobs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE compatibility.blobs FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON compatibility.blobs
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT USAGE ON SCHEMA platform TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON
          iam.user_profiles, iam.passkeys, iam.passkey_challenges,
          platform.company_signups, platform.membership_requests,
          platform.runtime_states, compatibility.blobs
          TO warehouse_os;

        UPDATE iam.users
        SET is_platform_owner = true
        WHERE id = (
          SELECT u.id
          FROM iam.users AS u
          JOIN iam.memberships AS m ON m.user_id = u.id
          WHERE u.active AND m.active AND m.role_level = 10
          ORDER BY u.created_at, u.id
          LIMIT 1
        )
        AND NOT EXISTS (SELECT 1 FROM iam.users WHERE is_platform_owner);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS compatibility.blobs;
        DROP TABLE IF EXISTS platform.runtime_states;
        DROP TABLE IF EXISTS platform.membership_requests;
        DROP TABLE IF EXISTS platform.company_signups;
        DROP SCHEMA IF EXISTS platform;
        DROP TABLE IF EXISTS iam.passkey_challenges;
        DROP TABLE IF EXISTS iam.passkeys;
        DROP TABLE IF EXISTS iam.user_profiles;
        ALTER TABLE iam.users DROP COLUMN IF EXISTS is_platform_owner;
        """
    )
