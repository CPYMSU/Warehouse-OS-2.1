"""Add the HDD-backed workspace database data plane and unified usage ledger.

Revision ID: 20260802_0054
Revises: 20260802_0053
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0054"
down_revision = "20260802_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE platform.storage_pools
          DROP CONSTRAINT storage_pools_purpose_check;
        ALTER TABLE platform.storage_pools
          ADD CONSTRAINT storage_pools_purpose_check
          CHECK (purpose IN (
            'hosted_data', 'hosted_database', 'core_code', 'archive'
          ));
        ALTER TABLE platform.storage_pools
          DROP CONSTRAINT storage_pools_root_setting_check;
        ALTER TABLE platform.storage_pools
          ADD CONSTRAINT storage_pools_root_setting_check
          CHECK (root_setting IN (
            'asset_storage_root', 'asset_code_ssd_root',
            'hosted_database_root'
          ));

        INSERT INTO platform.storage_pools(
          pool_key, provider_key, label, storage_class, medium, purpose,
          root_setting, policy
        ) VALUES (
          'hosted-db-hdd-01', 'warehouse_postgresql_hdd_data_api',
          'Hosted PostgreSQL HDD', 'standard', 'hdd', 'hosted_database',
          'hosted_database_root',
          '{
            "required_for_workspace_database": true,
            "quota_accounting": "user_relations",
            "warning_percent": 75,
            "stop_expansion_percent": 88,
            "emergency_percent": 95
          }'::jsonb
        ) ON CONFLICT (pool_key) DO UPDATE SET
          provider_key = EXCLUDED.provider_key,
          label = EXCLUDED.label,
          storage_class = EXCLUDED.storage_class,
          medium = EXCLUDED.medium,
          purpose = EXCLUDED.purpose,
          root_setting = EXCLUDED.root_setting,
          policy = EXCLUDED.policy,
          updated_at = now();

        ALTER TABLE digital_asset.database_bindings
          ADD COLUMN pool_key text REFERENCES platform.storage_pools(pool_key),
          ADD COLUMN physical_medium text
            CHECK (physical_medium IN ('hdd', 'ssd', 'object')),
          ADD COLUMN database_ref text,
          ADD COLUMN role_ref text,
          ADD COLUMN actual_size_bytes bigint NOT NULL DEFAULT 0
            CHECK (actual_size_bytes >= 0),
          ADD COLUMN size_measured_at timestamptz,
          ADD COLUMN revision integer NOT NULL DEFAULT 1
            CHECK (revision > 0);

        UPDATE digital_asset.database_bindings
        SET physical_medium = 'ssd',
            config = config || '{
              "migration_state": "legacy_control_plane",
              "billable_size_source": "workspace_records"
            }'::jsonb
        WHERE provider_key = 'warehouse_postgresql_data_api';

        CREATE TABLE digital_asset.database_credentials (
          tenant_id uuid NOT NULL,
          database_binding_id uuid NOT NULL,
          secret_ciphertext text NOT NULL
            CHECK (secret_ciphertext LIKE 'fernet:v1:%'),
          key_version integer NOT NULL DEFAULT 1 CHECK (key_version > 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          rotated_at timestamptz,
          PRIMARY KEY (tenant_id, database_binding_id),
          FOREIGN KEY (tenant_id, database_binding_id)
            REFERENCES digital_asset.database_bindings(tenant_id, id)
            ON DELETE CASCADE
        );

        CREATE TABLE digital_asset.workspace_usage (
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          code_bytes bigint NOT NULL DEFAULT 0 CHECK (code_bytes >= 0),
          data_object_bytes bigint NOT NULL DEFAULT 0
            CHECK (data_object_bytes >= 0),
          database_bytes bigint NOT NULL DEFAULT 0 CHECK (database_bytes >= 0),
          runtime_bytes bigint NOT NULL DEFAULT 0 CHECK (runtime_bytes >= 0),
          total_billable_bytes bigint GENERATED ALWAYS AS (
            code_bytes + data_object_bytes + database_bytes + runtime_bytes
          ) STORED,
          measured_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          PRIMARY KEY (tenant_id, workspace_id),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE
        );

        INSERT INTO digital_asset.workspace_usage(
          tenant_id, workspace_id, code_bytes, data_object_bytes,
          database_bytes, runtime_bytes
        )
        SELECT w.tenant_id, w.id,
               COALESCE(SUM(a.size_bytes) FILTER (
                 WHERE a.storage_role = 'code'
                   AND a.state IN ('pending','stored','verified','quarantined','released')
               ), 0)::bigint,
               COALESCE(SUM(a.size_bytes) FILTER (
                 WHERE a.storage_role = 'data'
                   AND a.state IN ('pending','stored','verified','quarantined','released')
               ), 0)::bigint,
               COALESCE((
                 SELECT SUM(d.actual_size_bytes)::bigint
                 FROM digital_asset.database_bindings AS d
                 WHERE d.workspace_id = w.id
               ), 0),
               0
        FROM digital_asset.workspaces AS w
        LEFT JOIN digital_asset.artifacts AS a ON a.asset_id = w.asset_id
        GROUP BY w.tenant_id, w.id;

        CREATE TRIGGER trg_workspace_usage_updated
          BEFORE UPDATE ON digital_asset.workspace_usage
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE digital_asset.database_credentials ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.database_credentials FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.database_credentials
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE digital_asset.workspace_usage ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.workspace_usage FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.workspace_usage
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT SELECT, INSERT, UPDATE, DELETE
          ON digital_asset.database_credentials TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE
          ON digital_asset.workspace_usage TO warehouse_os;

        COMMENT ON TABLE digital_asset.database_credentials IS
          'Encrypted internal credentials for dedicated HDD workspace databases; '
          'never returned through the Data API or AI context.';
        COMMENT ON TABLE digital_asset.workspace_usage IS
          'One logical quota ledger combining SSD code, HDD objects, hosted '
          'PostgreSQL user relations and runtime persistent bytes.';

        INSERT INTO app.resource_fields(
          resource_key, field_key, label, semantic_description, data_type,
          nullable, editable_mode, sensitivity, storage_column, json_path,
          constraints, display_order
        ) VALUES
          ('digital_asset.database_binding','pool_key','資料庫儲存池','資料庫實體所在的受治理儲存池','string',true,'adapter_only','normal','pool_key','[]','{}',70),
          ('digital_asset.database_binding','physical_medium','實體介質','資料庫資料檔案所在 HDD/SSD 介質','string',true,'derived','normal','physical_medium','[]','{"enum":["hdd","ssd","object"]}',80),
          ('digital_asset.database_binding','actual_size_bytes','實際用量','用戶資料表、索引與 TOAST 的實際位元組數','integer',false,'derived','normal','actual_size_bytes','[]','{"minimum":"0"}',90),
          ('digital_asset.database_binding','size_measured_at','量測時間','最近一次資料庫實際用量量測時間','datetime',true,'derived','normal','size_measured_at','[]','{}',100)
        ON CONFLICT (resource_key, field_key) DO UPDATE SET
          label = EXCLUDED.label,
          semantic_description = EXCLUDED.semantic_description,
          data_type = EXCLUDED.data_type,
          nullable = EXCLUDED.nullable,
          editable_mode = EXCLUDED.editable_mode,
          sensitivity = EXCLUDED.sensitivity,
          storage_column = EXCLUDED.storage_column,
          constraints = EXCLUDED.constraints,
          display_order = EXCLUDED.display_order;

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES (
          'digital_asset.database_binding.hosted_data_hdd',
          'digital_asset.database_binding',
          '用戶軟件的業務資料庫必須位於 HDD，平台控制資料庫不屬於此綁定',
          'domain_adapter',
          '{"required_provider":"warehouse_postgresql_hdd_data_api","physical_medium":"hdd","native_dsn_exposed": false}'
        ) ON CONFLICT (invariant_key) DO UPDATE SET
          description = EXCLUDED.description,
          enforcement = EXCLUDED.enforcement,
          machine_contract = EXCLUDED.machine_contract,
          active = true;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS digital_asset.workspace_usage;
        DROP TABLE IF EXISTS digital_asset.database_credentials;
        DELETE FROM app.resource_invariants
        WHERE invariant_key = 'digital_asset.database_binding.hosted_data_hdd';
        DELETE FROM app.resource_fields
        WHERE resource_key = 'digital_asset.database_binding'
          AND field_key IN (
            'pool_key', 'physical_medium', 'actual_size_bytes', 'size_measured_at'
          );
        ALTER TABLE digital_asset.database_bindings
          DROP COLUMN IF EXISTS revision,
          DROP COLUMN IF EXISTS size_measured_at,
          DROP COLUMN IF EXISTS actual_size_bytes,
          DROP COLUMN IF EXISTS role_ref,
          DROP COLUMN IF EXISTS database_ref,
          DROP COLUMN IF EXISTS physical_medium,
          DROP COLUMN IF EXISTS pool_key;
        DELETE FROM platform.storage_pools WHERE pool_key = 'hosted-db-hdd-01';
        ALTER TABLE platform.storage_pools
          DROP CONSTRAINT storage_pools_purpose_check;
        ALTER TABLE platform.storage_pools
          ADD CONSTRAINT storage_pools_purpose_check
          CHECK (purpose IN ('hosted_data', 'core_code', 'archive'));
        ALTER TABLE platform.storage_pools
          DROP CONSTRAINT storage_pools_root_setting_check;
        ALTER TABLE platform.storage_pools
          ADD CONSTRAINT storage_pools_root_setting_check
          CHECK (root_setting IN ('asset_storage_root', 'asset_code_ssd_root'));
        """
    )
