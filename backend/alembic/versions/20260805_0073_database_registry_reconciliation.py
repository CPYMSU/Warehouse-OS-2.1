"""Backfill and enforce the workspace database service registry.

Revision ID: 20260805_0073
Revises: 20260804_0072
"""

from alembic import op

revision = "20260805_0073"
down_revision = "20260804_0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH safe_candidates AS MATERIALIZED (
          SELECT tenant_id,workspace_id,(array_agg(id))[1] AS binding_id
          FROM digital_asset.database_bindings
          GROUP BY tenant_id,workspace_id
          HAVING count(*)=1
             AND count(*) FILTER (WHERE is_default)=0
        ), updated AS (
          UPDATE digital_asset.database_bindings AS binding
          SET is_default=true,revision=revision+1,updated_at=now()
          FROM safe_candidates AS candidate
          WHERE binding.id=candidate.binding_id
          RETURNING binding.tenant_id,binding.workspace_id,binding.id,
                    binding.logical_name,binding.provider_key
        )
        INSERT INTO audit.events(tenant_id,actor_user_id,event_type,payload)
        SELECT tenant_id,NULL,'digital_asset.database_registry_backfilled',
               jsonb_build_object(
                 'workspace_id',workspace_id,
                 'database_binding_id',id,
                 'logical_name',logical_name,
                 'provider_key',provider_key,
                 'reason','sole_existing_binding_had_no_default'
               )
        FROM updated;

        CREATE OR REPLACE FUNCTION
          digital_asset.ensure_workspace_default_database()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          target_workspace uuid;
          binding_count integer;
          default_count integer;
        BEGIN
          IF TG_OP='DELETE' THEN
            target_workspace := OLD.workspace_id;
          ELSE
            target_workspace := NEW.workspace_id;
          END IF;
          SELECT count(*),count(*) FILTER (WHERE is_default)
          INTO binding_count,default_count
          FROM digital_asset.database_bindings
          WHERE workspace_id=target_workspace;
          IF binding_count>0 AND default_count<>1 THEN
            RAISE EXCEPTION
              'workspace % must have exactly one default database binding; found % of %',
              target_workspace,default_count,binding_count;
          END IF;

          IF TG_OP='UPDATE' AND OLD.workspace_id IS DISTINCT FROM NEW.workspace_id THEN
            SELECT count(*),count(*) FILTER (WHERE is_default)
            INTO binding_count,default_count
            FROM digital_asset.database_bindings
            WHERE workspace_id=OLD.workspace_id;
            IF binding_count>0 AND default_count<>1 THEN
              RAISE EXCEPTION
                'workspace % must have exactly one default database binding; found % of %',
                OLD.workspace_id,default_count,binding_count;
            END IF;
          END IF;
          RETURN NULL;
        END;
        $$;

        CREATE CONSTRAINT TRIGGER trg_workspace_default_database_required
          AFTER INSERT OR UPDATE OR DELETE
          ON digital_asset.database_bindings
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW
          EXECUTE FUNCTION digital_asset.ensure_workspace_default_database();

        INSERT INTO app.resource_invariants(
          invariant_key,resource_key,description,enforcement,machine_contract
        ) VALUES (
          'digital_asset.database_binding.exactly_one_default',
          'digital_asset.database_binding',
          '每個存在資料庫綁定的工作區必須且只能有一個預設資料庫，使 Runtime 與服務登記冊解析同一規範實體',
          'database',
          jsonb_build_object(
            'scope','workspace',
            'minimum_default_bindings',1,
            'maximum_default_bindings',1,
            'empty_workspace_allowed',true
          )
        ) ON CONFLICT (invariant_key) DO UPDATE SET
          description=EXCLUDED.description,
          enforcement=EXCLUDED.enforcement,
          machine_contract=EXCLUDED.machine_contract,
          active=true;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key='digital_asset.database_binding.exactly_one_default';
        DROP TRIGGER IF EXISTS trg_workspace_default_database_required
          ON digital_asset.database_bindings;
        DROP FUNCTION IF EXISTS
          digital_asset.ensure_workspace_default_database();
        """
    )
