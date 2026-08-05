"""Separate managed database owner and Runtime application credentials.

Revision ID: 20260803_0069
Revises: 20260803_0068
"""

from alembic import op

revision = "20260803_0069"
down_revision = "20260803_0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE digital_asset.database_bindings
          ADD COLUMN runtime_role_ref text
            CHECK (
              runtime_role_ref IS NULL
              OR runtime_role_ref ~ '^[a-z][a-z0-9_]{1,62}$'
            );

        CREATE TABLE digital_asset.database_runtime_credentials (
          tenant_id uuid NOT NULL,
          database_binding_id uuid NOT NULL,
          role_ref text NOT NULL
            CHECK (role_ref ~ '^[a-z][a-z0-9_]{1,62}$'),
          secret_ciphertext text NOT NULL
            CHECK (secret_ciphertext LIKE 'fernet:v1:%'),
          key_version integer NOT NULL DEFAULT 1 CHECK (key_version > 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          rotated_at timestamptz,
          last_reconciled_at timestamptz,
          PRIMARY KEY (tenant_id, database_binding_id),
          FOREIGN KEY (tenant_id, database_binding_id)
            REFERENCES digital_asset.database_bindings(tenant_id, id)
            ON DELETE CASCADE
        );

        ALTER TABLE digital_asset.database_runtime_credentials ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.database_runtime_credentials FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation
          ON digital_asset.database_runtime_credentials
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
          WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

        GRANT SELECT, INSERT, UPDATE, DELETE
          ON digital_asset.database_runtime_credentials TO warehouse_os;

        COMMENT ON COLUMN digital_asset.database_bindings.role_ref IS
          'Managed database owner role used only by bounded migrations and provider operations.';
        COMMENT ON COLUMN digital_asset.database_bindings.runtime_role_ref IS
          'Non-owner, non-BYPASSRLS application role injected into normal workspace Runtime.';
        COMMENT ON TABLE digital_asset.database_runtime_credentials IS
          'Encrypted credentials for the bounded managed-database Runtime application role.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS digital_asset.database_runtime_credentials;
        ALTER TABLE digital_asset.database_bindings
          DROP COLUMN IF EXISTS runtime_role_ref;
        """
    )
