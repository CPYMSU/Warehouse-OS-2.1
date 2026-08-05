"""Add request-driven scale-to-zero lifecycle for hosted runtimes.

Revision ID: 20260805_0078
Revises: 20260805_0077
"""

from __future__ import annotations

from alembic import op

revision = "20260805_0078"
down_revision = "20260805_0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        ALTER TABLE digital_asset.deployments
          ADD COLUMN runtime_state text NOT NULL DEFAULT 'not_applicable'
            CHECK (runtime_state IN (
              'not_applicable','running','suspending','suspended',
              'wake_requested','waking','error'
            )),
          ADD COLUMN runtime_last_request_at timestamptz,
          ADD COLUMN runtime_wake_requested_at timestamptz,
          ADD COLUMN runtime_suspended_at timestamptz,
          ADD COLUMN runtime_state_changed_at timestamptz NOT NULL DEFAULT now(),
          ADD COLUMN runtime_wake_error text;

        UPDATE digital_asset.deployments
        SET runtime_state='running',
            runtime_last_request_at=now(),
            runtime_state_changed_at=now()
        WHERE status='ready' AND health='healthy'
          AND result->>'runtime_kind' IN ('python','node','container')
          AND COALESCE((result->>'public_route')::boolean, true)
          AND COALESCE(result->>'execution_mode', 'service')='service'
          AND jsonb_typeof(result->'container_names')='array'
          AND jsonb_array_length(result->'container_names') > 0;

        CREATE INDEX idx_deployments_runtime_lifecycle
          ON digital_asset.deployments(
            tenant_id, runtime_state, runtime_last_request_at
          )
          WHERE runtime_state != 'not_applicable';

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES (
          'digital_asset.runtime.request_driven_scale_to_zero',
          'digital_asset.deployment',
          '动态托管运行时空闲后释放内存；请求到达时原地启动保留在 SSD 上的容器并通过健康门禁',
          'domain_adapter',
          '{"idle_stop":true,"container_preserved":true,"request_wake":true,"health_gate":true,"static_containerless":true}'::jsonb
        ) ON CONFLICT (invariant_key) DO UPDATE SET
          description=EXCLUDED.description,
          enforcement=EXCLUDED.enforcement,
          machine_contract=EXCLUDED.machine_contract,
          active=true;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key='digital_asset.runtime.request_driven_scale_to_zero';
        DROP INDEX IF EXISTS digital_asset.idx_deployments_runtime_lifecycle;
        ALTER TABLE digital_asset.deployments
          DROP COLUMN IF EXISTS runtime_wake_error,
          DROP COLUMN IF EXISTS runtime_state_changed_at,
          DROP COLUMN IF EXISTS runtime_suspended_at,
          DROP COLUMN IF EXISTS runtime_wake_requested_at,
          DROP COLUMN IF EXISTS runtime_last_request_at,
          DROP COLUMN IF EXISTS runtime_state;
        """
    )
