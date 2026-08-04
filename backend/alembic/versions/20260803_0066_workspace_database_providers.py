"""Unify managed and customer-owned workspace database providers.

Revision ID: 20260803_0066
Revises: 20260803_0065
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0066"
down_revision = "20260803_0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE digital_asset.database_bindings
          DROP CONSTRAINT database_bindings_isolation_mode_check;
        ALTER TABLE digital_asset.database_bindings
          ADD CONSTRAINT database_bindings_isolation_mode_check
          CHECK (isolation_mode IN (
            'workspace_rls', 'dedicated_schema', 'dedicated_database',
            'dedicated_cluster', 'external_database'
          ));

        ALTER TABLE digital_asset.database_bindings
          ADD COLUMN ownership_mode text NOT NULL DEFAULT 'platform_managed'
            CHECK (ownership_mode IN ('platform_managed','customer_managed')),
          ADD COLUMN is_default boolean NOT NULL DEFAULT false,
          ADD COLUMN capabilities jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(capabilities)='object');

        UPDATE digital_asset.database_bindings
        SET capabilities = CASE
          WHEN provider_key='warehouse_postgresql_hdd_data_api' THEN
            '{
              "runtime_dsn": true,
              "collection_data_api": true,
              "relational_data_api": true,
              "schema_introspection": true,
              "migrations": true,
              "platform_backup": true,
              "platform_quota": true
            }'::jsonb
          ELSE
            '{
              "runtime_dsn": false,
              "collection_data_api": true,
              "relational_data_api": false,
              "schema_introspection": false,
              "migrations": false,
              "platform_backup": false,
              "platform_quota": true
            }'::jsonb
          END;

        WITH ranked AS (
          SELECT id,
                 row_number() OVER (
                   PARTITION BY tenant_id,workspace_id ORDER BY created_at,id
                 ) AS position
          FROM digital_asset.database_bindings
        )
        UPDATE digital_asset.database_bindings AS binding
        SET is_default=true
        FROM ranked
        WHERE ranked.id=binding.id AND ranked.position=1;

        CREATE UNIQUE INDEX uq_database_bindings_default
          ON digital_asset.database_bindings(tenant_id,workspace_id)
          WHERE is_default;

        ALTER TABLE digital_asset.database_credentials
          ADD COLUMN credential_kind text NOT NULL DEFAULT 'managed_password'
            CHECK (credential_kind IN ('managed_password','external_dsn')),
          ADD COLUMN last_validated_at timestamptz;

        INSERT INTO app.resource_fields(
          resource_key,field_key,label,semantic_description,data_type,
          nullable,editable_mode,sensitivity,storage_column,json_path,
          constraints,display_order
        ) VALUES
          ('digital_asset.database_binding','ownership_mode','所有權模式','資料庫由平台或客戶管理','string',false,'adapter_only','normal','ownership_mode','[]','{"enum":["platform_managed","customer_managed"]}',110),
          ('digital_asset.database_binding','is_default','預設資料庫','Runtime 的 DATABASE_URL 所使用的工作區預設綁定','boolean',false,'adapter_only','normal','is_default','[]','{}',120),
          ('digital_asset.database_binding','capabilities','提供者能力','此綁定可安全提供的 Runtime、Data API、遷移與備份能力','object',false,'derived','normal','capabilities','[]','{}',130)
        ON CONFLICT (resource_key,field_key) DO UPDATE SET
          label=EXCLUDED.label,
          semantic_description=EXCLUDED.semantic_description,
          data_type=EXCLUDED.data_type,
          nullable=EXCLUDED.nullable,
          editable_mode=EXCLUDED.editable_mode,
          sensitivity=EXCLUDED.sensitivity,
          storage_column=EXCLUDED.storage_column,
          constraints=EXCLUDED.constraints,
          display_order=EXCLUDED.display_order;

        UPDATE app.resource_invariants
        SET description='平台托管的用戶資料庫必須位於 HDD；客戶自有資料庫保留其外部儲存責任',
            machine_contract='{
              "managed_provider":"warehouse_postgresql_hdd_data_api",
              "managed_physical_medium":"hdd",
              "external_provider":"external_postgresql",
              "external_storage_responsibility":"customer",
              "native_dsn_exposed": false
            }'::jsonb,
            active=true
        WHERE invariant_key='digital_asset.database_binding.hosted_data_hdd';

        COMMENT ON COLUMN digital_asset.database_bindings.is_default IS
          'The single binding resolved into Runtime DATABASE_URL for this workspace.';
        COMMENT ON COLUMN digital_asset.database_bindings.capabilities IS
          'Provider facts consumed by Runtime, Data API, migration and backup adapters.';
        COMMENT ON COLUMN digital_asset.database_credentials.credential_kind IS
          'Discriminator for encrypted managed passwords and complete external DSNs.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM digital_asset.database_bindings
            WHERE provider_key='external_postgresql'
          ) THEN
            RAISE EXCEPTION 'Detach external database bindings before downgrade';
          END IF;
        END $$;

        DELETE FROM app.resource_fields
        WHERE resource_key='digital_asset.database_binding'
          AND field_key IN ('ownership_mode','is_default','capabilities');
        DROP INDEX IF EXISTS digital_asset.uq_database_bindings_default;
        ALTER TABLE digital_asset.database_credentials
          DROP COLUMN IF EXISTS last_validated_at,
          DROP COLUMN IF EXISTS credential_kind;
        ALTER TABLE digital_asset.database_bindings
          DROP COLUMN IF EXISTS capabilities,
          DROP COLUMN IF EXISTS is_default,
          DROP COLUMN IF EXISTS ownership_mode;
        ALTER TABLE digital_asset.database_bindings
          DROP CONSTRAINT database_bindings_isolation_mode_check;
        ALTER TABLE digital_asset.database_bindings
          ADD CONSTRAINT database_bindings_isolation_mode_check
          CHECK (isolation_mode IN (
            'workspace_rls','dedicated_schema','dedicated_database','dedicated_cluster'
          ));
        """
    )
