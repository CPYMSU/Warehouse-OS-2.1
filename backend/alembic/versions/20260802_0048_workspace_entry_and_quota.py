"""Give every hosted workspace a permanent entry and 512 MiB quota units.

Revision ID: 20260802_0048
Revises: 20260801_0047
"""

from sqlalchemy import text

from alembic import op

revision = "20260802_0048"
down_revision = "20260801_0047"
branch_labels = None
depends_on = None


QUOTA_STEP_BYTES = 512 * 1024 * 1024


def upgrade() -> None:
    op.execute(
        f"""
        ALTER TABLE digital_asset.workspaces
          ALTER COLUMN storage_quota_bytes SET DEFAULT {QUOTA_STEP_BYTES};

        UPDATE app.resource_fields
        SET editable_mode = 'adapter_only',
            semantic_description =
              '工作區正式儲存配額；預設 512 MiB，只能經配額適配器逐次增加 512 MiB',
            constraints = jsonb_build_object(
              'minimum', {QUOTA_STEP_BYTES},
              'multiple_of', {QUOTA_STEP_BYTES}
            )
        WHERE resource_key = 'digital_asset.workspace'
          AND field_key = 'storage_quota_bytes';

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description,
          enforcement, machine_contract, active
        ) VALUES (
          'digital_asset.workspace.quota_512_mib_steps',
          'digital_asset.workspace',
          '每個托管工作區預設 512 MiB；增加容量必須逐次申請 512 MiB 並保留審計',
          'domain_adapter',
          jsonb_build_object(
            'field', 'storage_quota_bytes',
            'default', {QUOTA_STEP_BYTES},
            'increase_step', {QUOTA_STEP_BYTES}
          ),
          true
        )
        ON CONFLICT (invariant_key) DO UPDATE SET
          description = EXCLUDED.description,
          enforcement = EXCLUDED.enforcement,
          machine_contract = EXCLUDED.machine_contract,
          active = true;
        """
    )
    bind = op.get_bind()
    tenant_ids = bind.execute(text("SELECT id FROM iam.tenants")).scalars().all()
    for tenant_id in tenant_ids:
        bind.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": tenant_id},
        )
        bind.execute(
            text(
                f"""
                UPDATE digital_asset.workspaces
                SET storage_quota_bytes = (
                  CEIL(
                    GREATEST(storage_quota_bytes, {QUOTA_STEP_BYTES})::numeric
                    / {QUOTA_STEP_BYTES}
                  ) * {QUOTA_STEP_BYTES}
                )::bigint
                WHERE tenant_id = :tenant_id
                  AND (
                    storage_quota_bytes < {QUOTA_STEP_BYTES}
                    OR MOD(storage_quota_bytes, {QUOTA_STEP_BYTES}) != 0
                  )
                """
            ),
            {"tenant_id": tenant_id},
        )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key = 'digital_asset.workspace.quota_512_mib_steps';

        UPDATE app.resource_fields
        SET editable_mode = 'direct',
            semantic_description = '工作區儲存配額位元組數',
            constraints = jsonb_build_object('minimum', '1')
        WHERE resource_key = 'digital_asset.workspace'
          AND field_key = 'storage_quota_bytes';

        ALTER TABLE digital_asset.workspaces
          ALTER COLUMN storage_quota_bytes SET DEFAULT 104857600;
        """
    )
