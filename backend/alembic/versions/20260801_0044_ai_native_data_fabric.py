"""Add the AI-native semantic resource and generic mutation fabric.

Revision ID: 20260801_0044
Revises: 20260801_0043
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0044"
down_revision = "20260801_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE app.resource_types (
          resource_key text PRIMARY KEY
            CHECK (resource_key ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'),
          schema_version integer NOT NULL DEFAULT 1 CHECK (schema_version > 0),
          label text NOT NULL CHECK (length(trim(label)) > 0),
          description text NOT NULL DEFAULT '',
          storage_adapter text NOT NULL DEFAULT 'postgres_table'
            CHECK (storage_adapter IN (
              'postgres_table', 'document_projection', 'remote_service'
            )),
          storage_schema text NOT NULL
            CHECK (storage_schema ~ '^[a-z][a-z0-9_]{0,62}$'),
          storage_table text NOT NULL
            CHECK (storage_table ~ '^[a-z][a-z0-9_]{0,62}$'),
          tenant_column text NOT NULL DEFAULT 'tenant_id'
            CHECK (tenant_column ~ '^[a-z][a-z0-9_]{0,62}$'),
          id_column text NOT NULL DEFAULT 'id'
            CHECK (id_column ~ '^[a-z][a-z0-9_]{0,62}$'),
          version_column text
            CHECK (
              version_column IS NULL
              OR version_column ~ '^[a-z][a-z0-9_]{0,62}$'
            ),
          version_strategy text NOT NULL DEFAULT 'none'
            CHECK (version_strategy IN ('none', 'integer', 'timestamp')),
          identity_fields jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(identity_fields) = 'array'),
          allowed_effects jsonb NOT NULL DEFAULT '["read"]'::jsonb
            CHECK (jsonb_typeof(allowed_effects) = 'array'),
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE app.resource_fields (
          resource_key text NOT NULL REFERENCES app.resource_types(resource_key)
            ON DELETE CASCADE,
          field_key text NOT NULL
            CHECK (field_key ~ '^[a-z][a-z0-9_]{0,62}$'),
          label text NOT NULL CHECK (length(trim(label)) > 0),
          semantic_description text NOT NULL DEFAULT '',
          data_type text NOT NULL
            CHECK (data_type IN (
              'string', 'integer', 'number', 'boolean', 'array', 'object',
              'uuid', 'datetime'
            )),
          data_format text,
          nullable boolean NOT NULL DEFAULT true,
          editable_mode text NOT NULL DEFAULT 'direct'
            CHECK (editable_mode IN (
              'direct', 'adapter_only', 'derived', 'immutable'
            )),
          sensitivity text NOT NULL DEFAULT 'normal'
            CHECK (sensitivity IN (
              'normal', 'personal', 'confidential', 'credential'
            )),
          storage_column text NOT NULL
            CHECK (storage_column ~ '^[a-z][a-z0-9_]{0,62}$'),
          json_path jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(json_path) = 'array'),
          constraints jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(constraints) = 'object'),
          examples jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(examples) = 'array'),
          display_order integer NOT NULL DEFAULT 100,
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (resource_key, field_key)
        );
        CREATE INDEX idx_resource_fields_resource_order
          ON app.resource_fields(resource_key, display_order, field_key)
          WHERE active;

        CREATE TABLE app.resource_relations (
          relation_key text PRIMARY KEY
            CHECK (relation_key ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'),
          source_resource_key text NOT NULL
            REFERENCES app.resource_types(resource_key) ON DELETE CASCADE,
          target_resource_key text NOT NULL
            REFERENCES app.resource_types(resource_key) ON DELETE CASCADE,
          source_field_key text NOT NULL,
          target_field_key text NOT NULL,
          cardinality text NOT NULL
            CHECK (cardinality IN ('one_to_one', 'many_to_one', 'one_to_many', 'many_to_many')),
          semantic_description text NOT NULL DEFAULT '',
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE app.resource_invariants (
          invariant_key text PRIMARY KEY
            CHECK (invariant_key ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'),
          resource_key text NOT NULL REFERENCES app.resource_types(resource_key)
            ON DELETE CASCADE,
          description text NOT NULL CHECK (length(trim(description)) > 0),
          enforcement text NOT NULL
            CHECK (enforcement IN (
              'database', 'domain_adapter', 'external_verification'
            )),
          machine_contract jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(machine_contract) = 'object'),
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE secretariat.data_mutations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          run_id uuid,
          conversation_id uuid,
          operation_id uuid NOT NULL,
          execution_identity text NOT NULL DEFAULT 'company_ai'
            CHECK (execution_identity IN ('company_ai', 'requesting_user')),
          origin text NOT NULL
            CHECK (origin IN (
              'auto_runtime', 'manual_ui', 'api', 'terminal', 'super_terminal'
            )),
          coverage text NOT NULL DEFAULT 'command_missing'
            CHECK (coverage IN ('command_missing', 'generic_native', 'promoted')),
          resource_key text NOT NULL REFERENCES app.resource_types(resource_key)
            ON DELETE RESTRICT,
          resource_id text NOT NULL,
          resource_ref text NOT NULL,
          effect text NOT NULL DEFAULT 'update'
            CHECK (effect IN ('create', 'update', 'archive', 'restore')),
          status text NOT NULL
            CHECK (status IN ('succeeded', 'rejected', 'conflict', 'failed')),
          intent text NOT NULL DEFAULT '',
          reasoning_summary text NOT NULL DEFAULT '',
          requested_changes jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(requested_changes) = 'object'),
          before_state jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(before_state) = 'object'),
          after_state jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(after_state) = 'object'),
          before_digest char(64) NOT NULL CHECK (before_digest ~ '^[a-f0-9]{64}$'),
          after_digest char(64) NOT NULL CHECK (after_digest ~ '^[a-f0-9]{64}$'),
          expected_version text,
          committed_version text,
          idempotency_key text NOT NULL CHECK (length(trim(idempotency_key)) BETWEEN 8 AND 240),
          authorization_keychain_id uuid,
          verification jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(verification) = 'object'),
          error text,
          created_at timestamptz NOT NULL DEFAULT now(),
          committed_at timestamptz,
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, idempotency_key)
        );
        CREATE INDEX idx_data_mutations_resource
          ON secretariat.data_mutations(
            tenant_id, resource_key, resource_id, created_at DESC
          );
        CREATE INDEX idx_data_mutations_run
          ON secretariat.data_mutations(tenant_id, run_id, created_at DESC)
          WHERE run_id IS NOT NULL;

        CREATE TABLE terminal.capability_gaps (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          fingerprint char(64) NOT NULL CHECK (fingerprint ~ '^[a-f0-9]{64}$'),
          resource_key text NOT NULL REFERENCES app.resource_types(resource_key)
            ON DELETE RESTRICT,
          effect text NOT NULL,
          field_set jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(field_set) = 'array'),
          occurrence_count integer NOT NULL DEFAULT 1 CHECK (occurrence_count > 0),
          examples jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(examples) = 'array'),
          suggested_tool_name text
            CHECK (
              suggested_tool_name IS NULL
              OR suggested_tool_name ~ '^[a-z][a-z0-9_]{1,127}$'
            ),
          promotion_reason text,
          status text NOT NULL DEFAULT 'observed'
            CHECK (status IN ('observed', 'reviewing', 'promoted', 'dismissed')),
          promoted_tool_name text,
          first_seen_at timestamptz NOT NULL DEFAULT now(),
          last_seen_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, fingerprint)
        );
        CREATE INDEX idx_capability_gaps_priority
          ON terminal.capability_gaps(
            tenant_id, status, occurrence_count DESC, last_seen_at DESC
          );

        CREATE TRIGGER trg_resource_types_updated
          BEFORE UPDATE ON app.resource_types
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_resource_fields_updated
          BEFORE UPDATE ON app.resource_fields
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE secretariat.data_mutations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE secretariat.data_mutations FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON secretariat.data_mutations
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE terminal.capability_gaps ENABLE ROW LEVEL SECURITY;
        ALTER TABLE terminal.capability_gaps FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON terminal.capability_gaps
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT SELECT ON app.resource_types, app.resource_fields,
          app.resource_relations, app.resource_invariants TO warehouse_os;
        GRANT SELECT, INSERT ON secretariat.data_mutations TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON terminal.capability_gaps TO warehouse_os;

        INSERT INTO app.resource_types(
          resource_key, label, description, storage_schema, storage_table,
          version_column, version_strategy, identity_fields, allowed_effects
        ) VALUES
          (
            'digital_asset.asset', '數字資產',
            '企業託管、部署及交易所使用的數字資產主檔',
            'digital_asset', 'assets', 'updated_at', 'timestamp',
            '["id","legacy_id","asset_no","name"]'::jsonb,
            '["read","query","update"]'::jsonb
          ),
          (
            'digital_asset.workspace', '託管工作區',
            '數字資產的站點、運行時、資料庫及組件工作區',
            'digital_asset', 'workspaces', 'revision', 'integer',
            '["id","legacy_id","workspace_key"]'::jsonb,
            '["read","query","update"]'::jsonb
          ),
          (
            'iam.organizational_unit', '組織單位',
            '公司、部門、研究中心、科研中心、實驗室、團隊或專案單位',
            'iam', 'organizational_units', 'updated_at', 'timestamp',
            '["id","unit_code","name"]'::jsonb,
            '["read","query","update"]'::jsonb
          ),
          (
            'iam.position_profile', '崗位',
            '部門內的崗位、職責、級別與能力語義',
            'iam', 'position_profiles', 'updated_at', 'timestamp',
            '["id","position_code","name"]'::jsonb,
            '["read","query","update"]'::jsonb
          );

        INSERT INTO app.resource_fields(
          resource_key, field_key, label, semantic_description, data_type,
          nullable, editable_mode, sensitivity, storage_column, json_path,
          constraints, display_order
        ) VALUES
          ('digital_asset.asset','asset_no','資產編號','穩定企業資產編號','string',false,'immutable','normal','asset_no','[]','{}',10),
          ('digital_asset.asset','name','名稱','數字資產名稱','string',false,'direct','normal','name','[]','{"min_length":"1","max_length":"200"}',20),
          ('digital_asset.asset','summary','說明','資產用途及內容摘要','string',true,'direct','normal','summary','[]','{}',30),
          ('digital_asset.asset','asset_kind','資產類型','資產本體類型；與工作區 runtime 類型不同','string',false,'direct','normal','asset_kind','[]','{"enum":["data","process","knowledge","software","model","agent","project","other"]}',40),
          ('digital_asset.asset','status','資產狀態','資產保管生命週期狀態','string',false,'adapter_only','normal','status','[]','{}',50),
          ('digital_asset.asset','lifecycle_stage','生命週期','資產從發現到退役的階段','string',false,'adapter_only','normal','lifecycle_stage','[]','{}',60),
          ('digital_asset.asset','risk_level','風險級別','資產當前風險判斷','string',false,'direct','normal','risk_level','[]','{"enum":["low","medium","high","critical"]}',70),
          ('digital_asset.asset','tags','標籤','可搜索的資產語義標籤','array',false,'direct','normal','tags','[]','{}',80),

          ('digital_asset.workspace','workspace_key','工作區代碼','穩定工作區識別碼','string',false,'immutable','normal','workspace_key','[]','{}',10),
          ('digital_asset.workspace','service_plan','服務計畫','custody、hosted、managed 或 dedicated','string',false,'adapter_only','normal','service_plan','[]','{}',20),
          ('digital_asset.workspace','status','工作區狀態','工作區存續狀態','string',false,'adapter_only','normal','status','[]','{}',30),
          ('digital_asset.workspace','runtime_status','運行狀態','由部署與運行時適配器維護','string',false,'derived','normal','runtime_status','[]','{}',40),
          ('digital_asset.workspace','runtime_type','運行類型','static、web、api、worker 或 agent；只修改配置，不宣稱已部署','string',false,'direct','normal','config','["runtime_type"]','{"enum":["static","web","api","worker","agent"]}',50),
          ('digital_asset.workspace','region','區域','工作區配置或運行區域','string',false,'direct','normal','region','[]','{"min_length":"1","max_length":"120"}',60),
          ('digital_asset.workspace','public_url','公開網址','工作區目前登記的公開網址','string',true,'direct','normal','public_url','[]','{"max_length":"1000"}',70),
          ('digital_asset.workspace','storage_quota_bytes','儲存配額','工作區儲存配額位元組數','integer',false,'direct','normal','storage_quota_bytes','[]','{"minimum":"1"}',80),

          ('iam.organizational_unit','unit_code','單位代碼','穩定組織單位代碼','string',false,'immutable','normal','unit_code','[]','{}',10),
          ('iam.organizational_unit','name','名稱','組織單位顯示名稱','string',false,'direct','normal','name','[]','{"min_length":"1","max_length":"200"}',20),
          ('iam.organizational_unit','name_en','英文名稱','組織單位英文名稱','string',true,'direct','normal','name_en','[]','{"max_length":"200"}',30),
          ('iam.organizational_unit','description','說明','組織單位職責及邊界','string',false,'direct','normal','description','[]','{}',40),
          ('iam.organizational_unit','unit_type','單位類型','company、department、team、project 或 other','string',false,'direct','normal','unit_type','[]','{"enum":["company","department","team","project","other"]}',50),
          ('iam.organizational_unit','parent_unit_code','上級單位','上級組織單位代碼','string',true,'direct','normal','parent_unit_code','[]','{}',60),
          ('iam.organizational_unit','active','啟用','是否在當前拓撲中生效','boolean',false,'adapter_only','normal','active','[]','{}',70),

          ('iam.position_profile','position_code','崗位代碼','穩定崗位識別碼','string',false,'immutable','normal','position_code','[]','{}',10),
          ('iam.position_profile','department_code','所屬單位','崗位所屬組織單位代碼','string',false,'direct','normal','department_code','[]','{}',20),
          ('iam.position_profile','name','名稱','崗位顯示名稱','string',false,'direct','normal','name','[]','{"min_length":"1","max_length":"200"}',30),
          ('iam.position_profile','name_en','英文名稱','崗位英文名稱','string',true,'direct','normal','name_en','[]','{"max_length":"200"}',40),
          ('iam.position_profile','role_name','角色名稱','崗位承擔的角色語義','string',false,'direct','normal','role_name','[]','{"min_length":"1","max_length":"200"}',50),
          ('iam.position_profile','role_level','角色級別','L1-L10 角色級別','integer',false,'adapter_only','normal','role_level','[]','{"minimum":"1","maximum":"10"}',60),
          ('iam.position_profile','is_manager','管理職','是否為管理崗位','boolean',false,'direct','normal','is_manager','[]','{}',70),
          ('iam.position_profile','permissions','能力證據','崗位能力集合；由權限拓撲適配器維護','array',false,'adapter_only','confidential','permissions','[]','{}',80),
          ('iam.position_profile','database_access','資料存取語義','崗位資料範圍；由權限拓撲適配器維護','object',false,'adapter_only','confidential','database_access','[]','{}',90),
          ('iam.position_profile','navigation_defaults','預設導航','崗位預設頁面集合','array',false,'direct','normal','navigation_defaults','[]','{}',100),
          ('iam.position_profile','public_entry','公開入口','崗位公開入口設定','object',true,'direct','normal','public_entry','[]','{}',110),
          ('iam.position_profile','case_roles','案件角色','可擔任的案件角色','array',false,'adapter_only','normal','case_roles','[]','{}',120),
          ('iam.position_profile','active','啟用','崗位是否有效','boolean',false,'adapter_only','normal','active','[]','{}',130);

        INSERT INTO app.resource_relations(
          relation_key, source_resource_key, target_resource_key,
          source_field_key, target_field_key, cardinality, semantic_description
        ) VALUES
          (
            'digital_asset.workspace.belongs_to_asset',
            'digital_asset.workspace', 'digital_asset.asset',
            'asset_id', 'id', 'many_to_one',
            '每個託管工作區必須屬於同一租戶的一個數字資產'
          ),
          (
            'iam.position_profile.belongs_to_unit',
            'iam.position_profile', 'iam.organizational_unit',
            'department_code', 'unit_code', 'many_to_one',
            '每個崗位必須屬於同一公司的有效組織單位'
          );

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES
          (
            'digital_asset.workspace.tenant_asset_fk',
            'digital_asset.workspace',
            '工作區與資產必須屬於同一租戶', 'database',
            '{"constraint":"workspace_tenant_asset_fk"}'::jsonb
          ),
          (
            'digital_asset.workspace.runtime_status_adapter',
            'digital_asset.workspace',
            'runtime_status 必須由部署或運行時適配器根據真實狀態更新',
            'domain_adapter', '{"field":"runtime_status"}'::jsonb
          ),
          (
            'iam.position_profile.department_fk',
            'iam.position_profile',
            '崗位所屬組織單位必須存在於同一租戶', 'database',
            '{"constraint":"position_department_fk"}'::jsonb
          );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS terminal.capability_gaps;
        DROP TABLE IF EXISTS secretariat.data_mutations;
        DROP TABLE IF EXISTS app.resource_invariants;
        DROP TABLE IF EXISTS app.resource_relations;
        DROP TABLE IF EXISTS app.resource_fields;
        DROP TABLE IF EXISTS app.resource_types;
        """
    )
