"""Backfill database registry defaults inside every tenant RLS context.

Revision ID: 20260805_0074
Revises: 20260805_0073
"""

from alembic import op

revision = "20260805_0074"
down_revision = "20260805_0073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
          tenant_row record;
        BEGIN
          FOR tenant_row IN SELECT id FROM iam.tenants ORDER BY id LOOP
            PERFORM set_config('app.tenant_id', tenant_row.id::text, true);

            WITH safe_candidates AS MATERIALIZED (
              SELECT (array_agg(binding.id))[1] AS binding_id
              FROM digital_asset.assets AS asset
              JOIN digital_asset.workspaces AS workspace
                ON workspace.asset_id=asset.id AND workspace.status='active'
              JOIN digital_asset.database_bindings AS binding
                ON binding.workspace_id=workspace.id
              WHERE asset.status<>'archived'
              GROUP BY workspace.id
              HAVING count(binding.id)=1
                 AND count(binding.id) FILTER (WHERE binding.is_default)=0
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
                     'reason','sole_existing_binding_had_no_default',
                     'rls_context','tenant_migration'
                   )
            FROM updated;
          END LOOP;
        END;
        $$;
        """
    )


def downgrade() -> None:
    # A canonical default is durable business state.  Downgrading code must not
    # erase a registry decision that may have been observed by clients.
    pass
