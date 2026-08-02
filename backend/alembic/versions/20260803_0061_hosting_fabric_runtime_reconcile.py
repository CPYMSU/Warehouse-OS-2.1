"""Align hosting fabric providers with runtime reconciliation.

Revision ID: 20260803_0061
Revises: 20260803_0060
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0061"
down_revision = "20260803_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        GRANT SELECT,INSERT,UPDATE ON platform.accelerator_pools TO warehouse_os;

        UPDATE platform.hosting_fabric_drivers
        SET desired_schema = '{
              "fields":{
                "action":"create|restore",
                "mode":"logical|point_in_time",
                "destination":"local|remote",
                "backup_id":"uuid",
                "label":"string",
                "target_time":"timestamp"
              }
            }'::jsonb,
            capability_contract = '{
              "logical":{"format":"custom","checksum":"sha256","ready":true},
              "point_in_time":{"requires":["wal_archive","base_backup","timeline_restore"]},
              "remote":{"requires":["encrypted_remote_object_store","retention_policy"]},
              "unsupported_provider_result":"durable_blocked_action"
            }'::jsonb,
            revision=revision+1,
            updated_at=now()
        WHERE driver_key='postgres.backup.v1';

        UPDATE platform.hosting_fabric_drivers
        SET capability_contract = capability_contract || '{
              "metrics":"docker_one_shot_cpu_memory",
              "reconciler":"runtime_worker",
              "cooldown":true,
              "load_balancing":"stable_request_hash"
            }'::jsonb,
            revision=revision+1,
            updated_at=now()
        WHERE driver_key='runtime.scaling.v1';

        UPDATE platform.hosting_fabric_drivers
        SET desired_schema = '{
              "fields":{
                "image":"string",
                "dockerfile":"string",
                "command":"string",
                "port":"integer",
                "health_path":"string",
                "component":"string"
              }
            }'::jsonb,
            revision=revision+1,
            updated_at=now()
        WHERE driver_key='oci.container.v1';

        UPDATE platform.hosting_fabric_drivers
        SET desired_schema = '{
              "fields":{
                "file":"string",
                "route_service":"string",
                "max_services":"integer"
              }
            }'::jsonb,
            revision=revision+1,
            updated_at=now()
        WHERE driver_key='oci.compose.v1';
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        REVOKE INSERT,UPDATE ON platform.accelerator_pools FROM warehouse_os;
        """
    )
