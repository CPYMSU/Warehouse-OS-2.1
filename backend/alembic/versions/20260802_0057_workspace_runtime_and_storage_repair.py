"""Repair legacy workspace bindings and expose source-led Runtime configuration.

Revision ID: 20260802_0057
Revises: 20260802_0056
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0057"
down_revision = "20260802_0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO digital_asset.storage_bindings(
          id, tenant_id, workspace_id, provider_key, object_prefix,
          binding_role, pool_key, storage_class, status, config
        )
        SELECT gen_random_uuid(), w.tenant_id, w.id,
               'content_addressed_hdd',
               'tenants/' || w.tenant_id || '/workspaces/' || w.id || '/data/',
               'data', 'hosted-hdd-01', 'standard', 'provisioning',
               jsonb_build_object(
                 'medium', 'hdd',
                 'selection', 'repaired_default',
                 'data_must_use_hdd', true
               )
        FROM digital_asset.workspaces AS w
        WHERE NOT EXISTS (
          SELECT 1 FROM digital_asset.storage_bindings AS b
          WHERE b.tenant_id=w.tenant_id AND b.workspace_id=w.id
            AND b.binding_role='data'
        )
        ON CONFLICT (tenant_id, workspace_id, binding_role) DO NOTHING;

        INSERT INTO digital_asset.storage_bindings(
          id, tenant_id, workspace_id, provider_key, object_prefix,
          binding_role, pool_key, storage_class, status, config
        )
        SELECT gen_random_uuid(), w.tenant_id, w.id,
               CASE WHEN w.config->>'code_storage'='ssd'
                 THEN 'content_addressed_ssd' ELSE 'content_addressed_hdd' END,
               'tenants/' || w.tenant_id || '/workspaces/' || w.id || '/code/',
               'code',
               CASE WHEN w.config->>'code_storage'='ssd'
                 THEN 'core-ssd-01' ELSE 'hosted-hdd-01' END,
               CASE WHEN w.config->>'code_storage'='ssd'
                 THEN 'performance' ELSE 'standard' END,
               'provisioning',
               jsonb_build_object(
                 'medium', CASE WHEN w.config->>'code_storage'='ssd' THEN 'ssd' ELSE 'hdd' END,
                 'selection', 'repaired_from_workspace_intent'
               )
        FROM digital_asset.workspaces AS w
        WHERE NOT EXISTS (
          SELECT 1 FROM digital_asset.storage_bindings AS b
          WHERE b.tenant_id=w.tenant_id AND b.workspace_id=w.id
            AND b.binding_role='code'
        )
        ON CONFLICT (tenant_id, workspace_id, binding_role) DO NOTHING;

        UPDATE platform.runtime_profiles
        SET detector_contract = CASE runtime_family
          WHEN 'static' THEN '{"evidence":["index.html"],"workspace_types":["static","web"]}'::jsonb
          WHEN 'python' THEN '{"evidence_any":["requirements.txt","pyproject.toml","app.py","main.py","worker.py","agent.py"],"workspace_types":["web","api","worker","agent"]}'::jsonb
          WHEN 'node' THEN '{"evidence":["package.json"],"workspace_types":["web","api","worker","agent"]}'::jsonb
          ELSE detector_contract END,
            updated_at=now();

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES (
          'digital_asset.storage_binding.write_verified',
          'digital_asset.storage_binding',
          'ready 不能只来自配置；上传前必须通过 create/write/fsync/read/delete 探针',
          'domain_adapter',
          jsonb_build_object(
            'probe', 'create_write_fsync_read_delete',
            'failure_status', 'failed',
            'self_heal_missing_binding', true
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
        WHERE invariant_key='digital_asset.storage_binding.write_verified';
        """
    )
