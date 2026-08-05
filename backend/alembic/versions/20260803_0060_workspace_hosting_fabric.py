"""Add the data-driven advanced workspace hosting fabric.

Revision ID: 20260803_0060
Revises: 20260802_0059
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0060"
down_revision = "20260802_0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        ALTER TABLE platform.runtime_profiles
          DROP CONSTRAINT IF EXISTS runtime_profiles_runtime_family_check;
        ALTER TABLE platform.runtime_profiles
          ADD CONSTRAINT runtime_profiles_runtime_family_check
          CHECK (runtime_family IN ('static', 'python', 'node', 'container'));

        INSERT INTO platform.runtime_profiles(
          profile_key, label, runtime_family, image_ref,
          detector_contract, execution_contract, resource_limits
        ) VALUES (
          'container.v1', 'OCI Container / Compose', 'container', NULL,
          '{"evidence_any":["Dockerfile","compose.yaml","compose.yml","docker-compose.yaml","docker-compose.yml"],"archive_required":true}'::jsonb,
          '{"port":8080,"health_path":"/health","rootless_contract":true,"host_network":false,"privileged":false}'::jsonb,
          '{"memory_mb":512,"cpus":0.5,"pids":128,"max_replicas":8,"max_services":16}'::jsonb
        ) ON CONFLICT (profile_key) DO UPDATE SET
          label=EXCLUDED.label,
          runtime_family=EXCLUDED.runtime_family,
          detector_contract=EXCLUDED.detector_contract,
          execution_contract=EXCLUDED.execution_contract,
          resource_limits=EXCLUDED.resource_limits,
          enabled=true,
          revision=platform.runtime_profiles.revision+1,
          updated_at=now();

        CREATE TABLE platform.hosting_fabric_drivers (
          driver_key text PRIMARY KEY
            CHECK (driver_key ~ '^[a-z][a-z0-9_.-]{2,79}$'),
          resource_kind text NOT NULL UNIQUE
            CHECK (resource_kind ~ '^[a-z][a-z0-9_.-]{2,79}$'),
          label text NOT NULL,
          description text NOT NULL,
          execution_mode text NOT NULL
            CHECK (execution_mode IN ('control_plane','runtime_worker','host_agent','provider')),
          required_scope text NOT NULL,
          desired_schema jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(desired_schema)='object'),
          capability_contract jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(capability_contract)='object'),
          enabled boolean NOT NULL DEFAULT true,
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER trg_hosting_fabric_drivers_updated
          BEFORE UPDATE ON platform.hosting_fabric_drivers
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        GRANT SELECT ON platform.hosting_fabric_drivers TO warehouse_os;

        INSERT INTO platform.hosting_fabric_drivers(
          driver_key, resource_kind, label, description, execution_mode,
          required_scope, desired_schema, capability_contract
        ) VALUES
          ('oci.container.v1','container','OCI 容器',
           '從已驗證源碼 Dockerfile 或受限 OCI image 建立無特權容器',
           'runtime_worker','infra:write',
           '{"fields":{"image":"string","dockerfile":"string","command":"string","port":"integer","health_path":"string"}}'::jsonb,
           '{"privileged":false,"host_network":false,"host_paths":false,"docker_socket":false}'::jsonb),
          ('oci.compose.v1','compose','多服務編排',
           '解析受限 Compose 服務圖並在工作區網路中部署多個服務',
           'runtime_worker','infra:write',
           '{"fields":{"file":"string","route_service":"string"}}'::jsonb,
           '{"max_services":16,"supported":["image","build","command","environment","depends_on","ports","healthcheck"],"forbidden":["privileged","network_mode","pid","ipc","devices","host_paths"]}'::jsonb),
          ('domain.acme.v1','domain','自訂網域與 TLS',
           '驗證網域指向後由受限主機代理配置 Nginx 與 ACME TLS',
           'host_agent','domain:write',
           '{"fields":{"hostname":"string","redirect_https":"boolean"}}'::jsonb,
           '{"ownership":"acme_http_01","tls":"letsencrypt","plaintext_key_exposed":false}'::jsonb),
          ('runtime.environment.v1','environment','環境變量',
           '把非秘密環境變量注入指定工作區組件或服務',
           'control_plane','infra:write',
           '{"fields":{"component":"string","variables":"object"}}'::jsonb,
           '{"reserved_prefix":"WAREHOUSE_","max_variables":128}'::jsonb),
          ('runtime.secret.v1','secret','秘密與憑證',
           '加密保存只寫秘密並在 Runtime 啟動時注入，永不返回明文',
           'control_plane','secrets:write',
           '{"fields":{"name":"string","value":"write_only_string","component":"string"}}'::jsonb,
           '{"encryption":"fernet.v1","plaintext_read":false,"versioned":true}'::jsonb),
          ('runtime.scaling.v1','scaling','擴縮容與負載均衡',
           '保存副本及自動擴縮策略並由 Runtime Worker 調和',
           'runtime_worker','infra:write',
           '{"fields":{"component":"string","min_replicas":"integer","max_replicas":"integer","target_cpu_percent":"integer"}}'::jsonb,
           '{"max_replicas":8,"strategy":"least_request_hash","health_required":true}'::jsonb),
          ('postgres.migration.v1','database_migration','資料庫 Migration',
           '在專屬工作區 PostgreSQL 角色內執行版本化交易式 DDL',
           'control_plane','database:admin',
           '{"fields":{"version":"string","sql":"string","checksum":"string"}}'::jsonb,
           '{"transactional":true,"workspace_role_only":true,"superuser":false,"immutable_history":true}'::jsonb),
          ('git.repository.v1','repository','Git 倉庫同步',
           '從 HTTPS Git 倉庫建立不可變已驗證源碼版本',
           'control_plane','repository:write',
           '{"fields":{"url":"string","ref":"string","credential_secret":"string","component":"string"}}'::jsonb,
           '{"protocols":["https"],"credentials":"secret_reference","shallow":true}'::jsonb),
          ('postgres.backup.v1','backup','備份與恢復',
           '建立加密可校驗的工作區資料庫備份並支援同工作區恢復',
           'control_plane','backup:write',
           '{"fields":{"action":"create|restore","backup_id":"uuid","label":"string"}}'::jsonb,
           '{"format":"logical_custom","checksum":"sha256","restore_boundary":"same_workspace"}'::jsonb),
          ('runtime.accelerator.v1','accelerator','GPU／加速器',
           '依可觀察資源池分配 GPU 或其他加速器並注入容器',
           'provider','accelerator:use',
           '{"fields":{"kind":"string","count":"integer","memory_mb":"integer","required":"boolean"}}'::jsonb,
           '{"allocation":"capacity_checked","exclusive_supported":true,"fallback":"explicit"}'::jsonb)
        ON CONFLICT (driver_key) DO UPDATE SET
          resource_kind=EXCLUDED.resource_kind,
          label=EXCLUDED.label,
          description=EXCLUDED.description,
          execution_mode=EXCLUDED.execution_mode,
          required_scope=EXCLUDED.required_scope,
          desired_schema=EXCLUDED.desired_schema,
          capability_contract=EXCLUDED.capability_contract,
          enabled=true,
          revision=platform.hosting_fabric_drivers.revision+1,
          updated_at=now();

        CREATE TABLE platform.accelerator_pools (
          pool_key text PRIMARY KEY CHECK (pool_key ~ '^[a-z][a-z0-9_.-]{2,79}$'),
          provider_key text NOT NULL,
          accelerator_kind text NOT NULL,
          total_units integer NOT NULL DEFAULT 0 CHECK (total_units >= 0),
          allocatable_units integer NOT NULL DEFAULT 0
            CHECK (allocatable_units >= 0 AND allocatable_units <= total_units),
          memory_mb_per_unit integer CHECK (memory_mb_per_unit IS NULL OR memory_mb_per_unit > 0),
          status text NOT NULL DEFAULT 'offline'
            CHECK (status IN ('online','degraded','offline','maintenance')),
          capabilities jsonb NOT NULL DEFAULT '{}'::jsonb,
          last_observed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER trg_accelerator_pools_updated
          BEFORE UPDATE ON platform.accelerator_pools
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        GRANT SELECT ON platform.accelerator_pools TO warehouse_os;

        CREATE TABLE digital_asset.hosting_resources (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          resource_kind text NOT NULL,
          resource_key text NOT NULL CHECK (length(trim(resource_key)) BETWEEN 1 AND 160),
          driver_key text NOT NULL REFERENCES platform.hosting_fabric_drivers(driver_key),
          desired_state jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(desired_state)='object'),
          observed_state jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(observed_state)='object'),
          status text NOT NULL DEFAULT 'planned'
            CHECK (status IN ('planned','queued','applying','ready','blocked','failed','suspended','deleted')),
          last_error jsonb CHECK (last_error IS NULL OR jsonb_typeof(last_error)='object'),
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          created_by_credential_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id,id),
          UNIQUE (tenant_id,workspace_id,resource_kind,resource_key),
          FOREIGN KEY (tenant_id,workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id,id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id,created_by_credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id,id) ON DELETE SET NULL
        );
        CREATE INDEX idx_hosting_resources_workspace
          ON digital_asset.hosting_resources(tenant_id,workspace_id,resource_kind,status);
        CREATE TRIGGER trg_hosting_resources_updated
          BEFORE UPDATE ON digital_asset.hosting_resources
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE TABLE digital_asset.hosting_secret_versions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          resource_id uuid NOT NULL,
          name text NOT NULL CHECK (name ~ '^[A-Z][A-Z0-9_]{0,126}$'),
          version integer NOT NULL CHECK (version > 0),
          ciphertext text NOT NULL,
          value_digest text NOT NULL CHECK (value_digest ~ '^[a-f0-9]{64}$'),
          active boolean NOT NULL DEFAULT true,
          created_by_credential_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          revoked_at timestamptz,
          UNIQUE (tenant_id,id),
          UNIQUE (tenant_id,workspace_id,name,version),
          FOREIGN KEY (tenant_id,workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id,id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id,resource_id)
            REFERENCES digital_asset.hosting_resources(tenant_id,id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id,created_by_credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id,id) ON DELETE SET NULL
        );
        CREATE UNIQUE INDEX uq_hosting_secret_active
          ON digital_asset.hosting_secret_versions(tenant_id,workspace_id,name)
          WHERE active AND revoked_at IS NULL;

        CREATE TABLE digital_asset.hosting_actions (
          id uuid PRIMARY KEY,
          legacy_id bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          resource_id uuid,
          action_type text NOT NULL,
          idempotency_key text,
          request_digest text NOT NULL CHECK (request_digest ~ '^[a-f0-9]{64}$'),
          status text NOT NULL DEFAULT 'queued'
            CHECK (status IN ('queued','running','succeeded','blocked','failed','cancelled')),
          request jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(request)='object'),
          result jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(result)='object'),
          error jsonb CHECK (error IS NULL OR jsonb_typeof(error)='object'),
          requested_by_credential_id uuid,
          lease_owner text,
          lease_expires_at timestamptz,
          attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          started_at timestamptz,
          completed_at timestamptz,
          UNIQUE (tenant_id,id),
          UNIQUE (tenant_id,workspace_id,idempotency_key),
          FOREIGN KEY (tenant_id,workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id,id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id,resource_id)
            REFERENCES digital_asset.hosting_resources(tenant_id,id) ON DELETE SET NULL,
          FOREIGN KEY (tenant_id,requested_by_credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id,id) ON DELETE SET NULL
        );
        CREATE INDEX idx_hosting_actions_queue
          ON digital_asset.hosting_actions(status,created_at)
          WHERE status IN ('queued','running');

        CREATE TABLE digital_asset.hosting_action_events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL,
          action_id uuid NOT NULL,
          sequence integer NOT NULL CHECK (sequence > 0),
          event_type text NOT NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload)='object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id,action_id,sequence),
          FOREIGN KEY (tenant_id,action_id)
            REFERENCES digital_asset.hosting_actions(tenant_id,id) ON DELETE CASCADE
        );
        CREATE INDEX idx_hosting_action_events
          ON digital_asset.hosting_action_events(tenant_id,action_id,sequence);
        CREATE TRIGGER trg_hosting_action_events_immutable
          BEFORE UPDATE OR DELETE ON digital_asset.hosting_action_events
          FOR EACH ROW EXECUTE FUNCTION digital_asset.reject_immutable_mutation();

        CREATE TABLE digital_asset.database_migration_history (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          database_binding_id uuid NOT NULL,
          version text NOT NULL CHECK (length(trim(version)) BETWEEN 1 AND 120),
          checksum text NOT NULL CHECK (checksum ~ '^[a-f0-9]{64}$'),
          statement_count integer NOT NULL CHECK (statement_count > 0),
          status text NOT NULL CHECK (status IN ('applied','failed')),
          error text,
          applied_by_credential_id uuid,
          applied_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id,id),
          UNIQUE (tenant_id,workspace_id,database_binding_id,version),
          FOREIGN KEY (tenant_id,workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id,id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id,database_binding_id)
            REFERENCES digital_asset.database_bindings(tenant_id,id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id,applied_by_credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id,id) ON DELETE SET NULL
        );

        CREATE TABLE digital_asset.database_backups (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          database_binding_id uuid NOT NULL,
          label text NOT NULL,
          backup_kind text NOT NULL DEFAULT 'logical'
            CHECK (backup_kind IN ('logical','base','point_in_time')),
          storage_provider text NOT NULL,
          object_key text,
          sha256 text CHECK (sha256 IS NULL OR sha256 ~ '^[a-f0-9]{64}$'),
          size_bytes bigint NOT NULL DEFAULT 0 CHECK (size_bytes >= 0),
          status text NOT NULL DEFAULT 'creating'
            CHECK (status IN ('creating','ready','restoring','failed','expired')),
          recovery_point timestamptz NOT NULL DEFAULT now(),
          retention_until timestamptz,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by_credential_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          completed_at timestamptz,
          UNIQUE (tenant_id,id),
          FOREIGN KEY (tenant_id,workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id,id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id,database_binding_id)
            REFERENCES digital_asset.database_bindings(tenant_id,id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id,created_by_credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id,id) ON DELETE SET NULL
        );
        CREATE INDEX idx_database_backups_workspace
          ON digital_asset.database_backups(tenant_id,workspace_id,created_at DESC);

        GRANT SELECT,INSERT,UPDATE,DELETE ON digital_asset.hosting_resources TO warehouse_os;
        GRANT SELECT,INSERT,UPDATE ON digital_asset.hosting_secret_versions TO warehouse_os;
        GRANT SELECT,INSERT,UPDATE ON digital_asset.hosting_actions TO warehouse_os;
        GRANT SELECT,INSERT ON digital_asset.hosting_action_events TO warehouse_os;
        GRANT SELECT,INSERT ON digital_asset.database_migration_history TO warehouse_os;
        GRANT SELECT,INSERT,UPDATE ON digital_asset.database_backups TO warehouse_os;
        GRANT USAGE,SELECT ON SEQUENCE digital_asset.hosting_actions_legacy_id_seq TO warehouse_os;
        GRANT USAGE,SELECT ON SEQUENCE digital_asset.hosting_action_events_id_seq TO warehouse_os;

        ALTER TABLE digital_asset.hosting_resources ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.hosting_resources FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.hosting_resources
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());
        ALTER TABLE digital_asset.hosting_secret_versions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.hosting_secret_versions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.hosting_secret_versions
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());
        ALTER TABLE digital_asset.hosting_actions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.hosting_actions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.hosting_actions
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());
        ALTER TABLE digital_asset.hosting_action_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.hosting_action_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.hosting_action_events
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());
        ALTER TABLE digital_asset.database_migration_history ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.database_migration_history FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.database_migration_history
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());
        ALTER TABLE digital_asset.database_backups ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.database_backups FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.database_backups
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());

        UPDATE digital_asset.api_credentials
        SET scopes=ARRAY[
          'workspace:read','data:read','data:write','deploy:read','deploy:write','logs:read',
          'infra:read','infra:write','domain:write','secrets:write','database:admin',
          'repository:write','backup:write','accelerator:use'
        ]::text[]
        WHERE key_kind='primary' AND revoked_at IS NULL;

        INSERT INTO app.resource_types(
          resource_key,schema_version,label,description,storage_schema,storage_table,
          version_column,version_strategy,identity_fields,allowed_effects
        ) VALUES (
          'digital_asset.hosting_resource',1,'工作區託管資源',
          '由 AI desired state 驅動並以真實 observed state 覆核的可移植託管資源',
          'digital_asset','hosting_resources','revision','integer',
          '["id","resource_kind","resource_key"]'::jsonb,
          '["read","create","update"]'::jsonb
        ) ON CONFLICT (resource_key) DO UPDATE SET
          schema_version=EXCLUDED.schema_version,label=EXCLUDED.label,
          description=EXCLUDED.description,storage_schema=EXCLUDED.storage_schema,
          storage_table=EXCLUDED.storage_table,version_column=EXCLUDED.version_column,
          version_strategy=EXCLUDED.version_strategy,identity_fields=EXCLUDED.identity_fields,
          allowed_effects=EXCLUDED.allowed_effects,active=true;

        INSERT INTO app.resource_invariants(
          invariant_key,resource_key,description,enforcement,machine_contract
        ) VALUES (
          'digital_asset.hosting_resource.workspace_key_boundary',
          'digital_asset.hosting_resource',
          '所有高級託管操作都綁定同租戶同工作區並保留不可變動作事件；秘密永不返回明文',
          'database',
          '{"tenant_rls":true,"workspace_credential_bound":true,"events":"append_only","secret_plaintext_read":false,"desired_observed_separation":true}'::jsonb
        ) ON CONFLICT (invariant_key) DO UPDATE SET
          description=EXCLUDED.description,enforcement=EXCLUDED.enforcement,
          machine_contract=EXCLUDED.machine_contract,active=true;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key='digital_asset.hosting_resource.workspace_key_boundary';
        DELETE FROM app.resource_types
        WHERE resource_key='digital_asset.hosting_resource';
        DROP TABLE IF EXISTS digital_asset.database_backups;
        DROP TABLE IF EXISTS digital_asset.database_migration_history;
        DROP TABLE IF EXISTS digital_asset.hosting_action_events;
        DROP TABLE IF EXISTS digital_asset.hosting_actions;
        DROP TABLE IF EXISTS digital_asset.hosting_secret_versions;
        DROP TABLE IF EXISTS digital_asset.hosting_resources;
        DROP TABLE IF EXISTS platform.accelerator_pools;
        DROP TABLE IF EXISTS platform.hosting_fabric_drivers;
        DELETE FROM platform.runtime_profiles WHERE profile_key='container.v1';
        ALTER TABLE platform.runtime_profiles
          DROP CONSTRAINT IF EXISTS runtime_profiles_runtime_family_check;
        ALTER TABLE platform.runtime_profiles
          ADD CONSTRAINT runtime_profiles_runtime_family_check
          CHECK (runtime_family IN ('static','python','node'));
        """
    )
