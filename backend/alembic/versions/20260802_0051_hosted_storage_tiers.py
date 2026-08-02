"""Add observable HDD/SSD storage pools and role-based workspace bindings.

Revision ID: 20260802_0051
Revises: 20260802_0050
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0051"
down_revision = "20260802_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE platform.storage_pools (
          pool_key text PRIMARY KEY CHECK (pool_key ~ '^[a-z][a-z0-9-]{2,63}$'),
          provider_key text NOT NULL UNIQUE
            CHECK (provider_key ~ '^[a-z][a-z0-9_]{2,95}$'),
          label text NOT NULL CHECK (length(trim(label)) > 0),
          storage_class text NOT NULL
            CHECK (storage_class IN ('standard', 'performance', 'archive')),
          medium text NOT NULL CHECK (medium IN ('hdd', 'ssd', 'object')),
          purpose text NOT NULL
            CHECK (purpose IN ('hosted_data', 'core_code', 'archive')),
          root_setting text NOT NULL
            CHECK (root_setting IN ('asset_storage_root', 'asset_code_ssd_root')),
          status text NOT NULL DEFAULT 'ready'
            CHECK (status IN ('ready', 'degraded', 'draining', 'unavailable')),
          enabled boolean NOT NULL DEFAULT true,
          policy jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(policy) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        INSERT INTO platform.storage_pools(
          pool_key, provider_key, label, storage_class, medium, purpose,
          root_setting, policy
        ) VALUES
          (
            'hosted-hdd-01', 'content_addressed_hdd', 'Hosted HDD',
            'standard', 'hdd', 'hosted_data', 'asset_storage_root',
            '{
              "default_for_code": true,
              "required_for_data": true,
              "quota_step_bytes": 536870912,
              "warning_percent": 75,
              "stop_expansion_percent": 88,
              "emergency_percent": 95
            }'::jsonb
          ),
          (
            'core-ssd-01', 'content_addressed_ssd', 'Core Code SSD',
            'performance', 'ssd', 'core_code', 'asset_code_ssd_root',
            '{
              "explicit_opt_in": true,
              "allowed_roles": ["code"],
              "warning_percent": 80,
              "stop_expansion_percent": 90,
              "emergency_percent": 96
            }'::jsonb
          );

        CREATE TRIGGER trg_storage_pools_updated
          BEFORE UPDATE ON platform.storage_pools
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        GRANT SELECT ON platform.storage_pools TO warehouse_os;

        ALTER TABLE digital_asset.storage_bindings
          ADD COLUMN binding_role text NOT NULL DEFAULT 'data'
            CHECK (binding_role IN ('code', 'data')),
          ADD COLUMN pool_key text REFERENCES platform.storage_pools(pool_key)
            ON DELETE RESTRICT,
          ADD COLUMN storage_class text NOT NULL DEFAULT 'standard'
            CHECK (storage_class IN ('standard', 'performance', 'archive'));

        ALTER TABLE digital_asset.storage_bindings
          DROP CONSTRAINT IF EXISTS storage_bindings_tenant_id_workspace_id_key;
        ALTER TABLE digital_asset.storage_bindings
          ADD CONSTRAINT uq_storage_bindings_workspace_role
          UNIQUE (tenant_id, workspace_id, binding_role);

        UPDATE digital_asset.storage_bindings
        SET binding_role = 'data',
            pool_key = 'hosted-hdd-01',
            provider_key = 'content_addressed_hdd',
            storage_class = 'standard',
            config = config || '{"medium":"hdd","data_must_use_hdd": true}'::jsonb;

        INSERT INTO digital_asset.storage_bindings(
          id, tenant_id, workspace_id, provider_key, object_prefix,
          binding_role, pool_key, storage_class, config
        )
        SELECT gen_random_uuid(), w.tenant_id, w.id, 'content_addressed_hdd',
               'tenants/' || w.tenant_id || '/workspaces/' || w.id || '/code/',
               'code', 'hosted-hdd-01', 'standard',
               '{"medium":"hdd","selection":"default"}'::jsonb
        FROM digital_asset.workspaces AS w
        ON CONFLICT (tenant_id, workspace_id, binding_role) DO NOTHING;

        UPDATE digital_asset.workspaces
        SET config = config || '{"code_storage":"hdd","data_storage":"hdd"}'::jsonb;

        ALTER TABLE digital_asset.artifacts
          ADD COLUMN storage_role text NOT NULL DEFAULT 'data'
            CHECK (storage_role IN ('code', 'data')),
          ADD COLUMN storage_pool_key text
            REFERENCES platform.storage_pools(pool_key) ON DELETE RESTRICT;

        UPDATE digital_asset.artifacts
        SET storage_role = CASE
              WHEN artifact_kind IN ('package','source','frontend','backend','agent')
                THEN 'code'
              ELSE 'data'
            END,
            storage_pool_key = CASE
              WHEN storage_provider = 'content_addressed_local'
                THEN 'hosted-hdd-01'
              ELSE NULL
            END;

        INSERT INTO app.resource_fields(
          resource_key, field_key, label, semantic_description, data_type,
          nullable, editable_mode, sensitivity, storage_column, json_path,
          constraints, display_order
        ) VALUES
          ('digital_asset.workspace','code_storage','核心代碼儲存','預設 HDD；只有明確聲明時使用 SSD','string',false,'adapter_only','normal','config','["code_storage"]','{"enum":["hdd","ssd"]}',90),
          ('digital_asset.workspace','data_storage','托管資料儲存','附件、資料與持久化資料固定使用 HDD','string',false,'derived','normal','config','["data_storage"]','{"enum":["hdd"]}',100),
          ('digital_asset.artifact','storage_role','儲存角色','code 或 data；data 永遠使用 HDD','string',false,'immutable','normal','storage_role','[]','{"enum":["code","data"]}',80),
          ('digital_asset.artifact','storage_pool_key','儲存池','實際承載物件的可觀察儲存池','string',true,'immutable','normal','storage_pool_key','[]','{}',90),
          ('digital_asset.storage_binding','binding_role','綁定角色','code 或 data 的獨立儲存綁定','string',false,'immutable','normal','binding_role','[]','{"enum":["code","data"]}',5),
          ('digital_asset.storage_binding','pool_key','儲存池','平台儲存池識別碼','string',true,'adapter_only','normal','pool_key','[]','{}',15),
          ('digital_asset.storage_binding','storage_class','儲存級別','standard、performance 或 archive','string',false,'derived','normal','storage_class','[]','{}',25)
        ON CONFLICT (resource_key, field_key) DO UPDATE SET
          label = EXCLUDED.label,
          semantic_description = EXCLUDED.semantic_description,
          constraints = EXCLUDED.constraints,
          active = true;

        UPDATE app.resource_relations
        SET cardinality = 'many_to_one',
            semantic_description = '每個工作區有 code 與 data 兩個角色綁定；data 強制 HDD，code 預設 HDD 且可明確選 SSD'
        WHERE relation_key = 'digital_asset.storage_binding.belongs_to_workspace';

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES
          (
            'digital_asset.workspace.data_on_hdd',
            'digital_asset.workspace',
            '所有托管資料必須走 data 角色及 HDD 儲存池；核心代碼未明確選擇時也使用 HDD',
            'domain_adapter',
            '{"data_storage":"hdd","default_code_storage":"hdd","ssd_requires_explicit_intent": true}'::jsonb
          ),
          (
            'digital_asset.artifact.role_pool_binding',
            'digital_asset.artifact',
            '附件按 code/data 角色路由，服務端閘道強制核對工作區儲存綁定',
            'domain_adapter',
            '{"code_kinds":["package","source","frontend","backend","agent"],"data_medium":"hdd"}'::jsonb
          )
        ON CONFLICT (invariant_key) DO UPDATE SET
          description = EXCLUDED.description,
          machine_contract = EXCLUDED.machine_contract,
          active = true;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key IN (
          'digital_asset.workspace.data_on_hdd',
          'digital_asset.artifact.role_pool_binding'
        );
        DELETE FROM app.resource_fields
        WHERE (resource_key = 'digital_asset.workspace' AND field_key IN ('code_storage','data_storage'))
           OR (resource_key = 'digital_asset.artifact' AND field_key IN ('storage_role','storage_pool_key'))
           OR (resource_key = 'digital_asset.storage_binding' AND field_key IN ('binding_role','pool_key','storage_class'));
        UPDATE app.resource_relations
        SET cardinality = 'one_to_one',
            semantic_description = '儲存綁定屬於一個工作區'
        WHERE relation_key = 'digital_asset.storage_binding.belongs_to_workspace';

        DELETE FROM digital_asset.storage_bindings WHERE binding_role = 'code';
        ALTER TABLE digital_asset.artifacts
          DROP COLUMN IF EXISTS storage_pool_key,
          DROP COLUMN IF EXISTS storage_role;
        ALTER TABLE digital_asset.storage_bindings
          DROP CONSTRAINT IF EXISTS uq_storage_bindings_workspace_role;
        ALTER TABLE digital_asset.storage_bindings
          DROP COLUMN IF EXISTS storage_class,
          DROP COLUMN IF EXISTS pool_key,
          DROP COLUMN IF EXISTS binding_role;
        ALTER TABLE digital_asset.storage_bindings
          ADD CONSTRAINT storage_bindings_tenant_id_workspace_id_key
          UNIQUE (tenant_id, workspace_id);
        DROP TABLE IF EXISTS platform.storage_pools;
        """
    )
