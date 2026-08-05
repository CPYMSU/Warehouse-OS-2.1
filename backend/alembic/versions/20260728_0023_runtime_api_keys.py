"""Add tenant-bound API keys for the shared AI secretary and terminal Runtime.

Revision ID: 20260728_0023
Revises: 20260728_0022
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op

revision = "20260728_0023"
down_revision = "20260728_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.runtime_api_keys (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          owner_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
          public_id char(12) NOT NULL CHECK (public_id ~ '^[0-9a-f]{12}$'),
          label text NOT NULL CHECK (length(trim(label)) BETWEEN 1 AND 80),
          key_hash char(64) NOT NULL CHECK (key_hash ~ '^[0-9a-f]{64}$'),
          key_hint text NOT NULL CHECK (length(trim(key_hint)) > 0),
          scopes jsonb NOT NULL CHECK (
            jsonb_typeof(scopes) = 'array'
            AND scopes <@ '["assistant", "terminal"]'::jsonb
            AND jsonb_array_length(scopes) BETWEEN 1 AND 2
          ),
          expires_at timestamptz NOT NULL,
          revoked_at timestamptz,
          revoked_by_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          last_used_at timestamptz,
          use_count bigint NOT NULL DEFAULT 0 CHECK (use_count >= 0),
          created_by_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, public_id),
          UNIQUE (key_hash),
          UNIQUE (tenant_id, id)
        );

        CREATE INDEX idx_runtime_api_keys_owner
          ON iam.runtime_api_keys(
            tenant_id, owner_user_id, revoked_at, expires_at, id DESC
          );
        CREATE INDEX idx_runtime_api_keys_lookup
          ON iam.runtime_api_keys(tenant_id, public_id)
          WHERE revoked_at IS NULL;

        ALTER TABLE iam.runtime_api_keys ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.runtime_api_keys FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.runtime_api_keys
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT SELECT, INSERT, UPDATE, DELETE ON iam.runtime_api_keys TO warehouse_os;
        GRANT USAGE, SELECT ON SEQUENCE iam.runtime_api_keys_id_seq TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS iam.runtime_api_keys;")
