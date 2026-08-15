"""Register the release orchestration semantic contract on the primary.

Revision ID: 20260815_0095
Revises: 20260815_0094
"""

from __future__ import annotations

from alembic import op

revision = "20260815_0095"
down_revision = "20260815_0094"
branch_labels = None
depends_on = None
warehouse_scope = "primary_data"


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO app.resource_types(
          resource_key, schema_version, label, description,
          storage_schema, storage_table, version_column, version_strategy,
          identity_fields, allowed_effects
        ) VALUES (
          'digital_asset.release_session', 1, '工作區發布會話',
          '跨客戶端斷線可恢復的候選建置、生命週期任務、驗收、激活與回滾狀態',
          'digital_asset', 'release_sessions', 'updated_at', 'timestamp',
          '["id"]'::jsonb, '["read"]'::jsonb
        ) ON CONFLICT (resource_key) DO UPDATE SET
          schema_version=EXCLUDED.schema_version,
          label=EXCLUDED.label,
          description=EXCLUDED.description,
          storage_schema=EXCLUDED.storage_schema,
          storage_table=EXCLUDED.storage_table,
          version_column=EXCLUDED.version_column,
          version_strategy=EXCLUDED.version_strategy,
          identity_fields=EXCLUDED.identity_fields,
          allowed_effects=EXCLUDED.allowed_effects,
          active=true;

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES (
          'digital_asset.release_session.safe_activation',
          'digital_asset.release_session',
          '候選版本必須完成聲明式任務和驗收後才能由顯式請求激活；公共路由驗證失敗必須回滾',
          'domain_adapter',
          jsonb_build_object(
            'candidate_first', true,
            'manual_activation', true,
            'public_route_verification', true,
            'automatic_rollback', true,
            'append_only_events', true
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
          WHERE invariant_key='digital_asset.release_session.safe_activation';
        DELETE FROM app.resource_types
          WHERE resource_key='digital_asset.release_session';
        """
    )
