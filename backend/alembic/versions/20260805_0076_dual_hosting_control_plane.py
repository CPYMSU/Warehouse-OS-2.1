"""Add the user-selectable cloud/terminal hosting control plane.

Cloud hosting remains the default for every existing workspace.  Terminal
hosting is an opt-in execution target; the API and notification ledger let a
paired terminal or AI observe and acknowledge work without creating a server
Runtime.
"""

from __future__ import annotations

from alembic import op


revision = "20260805_0076"
down_revision = "20260805_0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE digital_asset.workspaces
          ADD COLUMN hosting_mode text NOT NULL DEFAULT 'cloud'
            CHECK (hosting_mode IN ('cloud', 'terminal')),
          ADD COLUMN compute_node text NOT NULL DEFAULT 'warehouse'
            CHECK (compute_node IN ('warehouse', 'vultr', 'mac_mini', 'user_terminal'));

        CREATE INDEX idx_digital_asset_workspaces_hosting_mode
          ON digital_asset.workspaces(tenant_id, hosting_mode, updated_at DESC);

        CREATE TABLE digital_asset.hosting_notifications (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          asset_id uuid NOT NULL,
          target text NOT NULL
            CHECK (target IN ('terminal', 'ai')),
          event_type text NOT NULL
            CHECK (event_type ~ '^[a-z][a-z0-9_.-]{2,79}$'),
          message text NOT NULL CHECK (length(trim(message)) BETWEEN 1 AND 2000),
          payload jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(payload) = 'object'),
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'acknowledged', 'expired', 'cancelled')),
          deployment_id uuid,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          delivered_at timestamptz,
          acknowledged_at timestamptz,
          expires_at timestamptz,
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, asset_id)
            REFERENCES digital_asset.assets(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, deployment_id)
            REFERENCES digital_asset.deployments(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_hosting_notifications_pending
          ON digital_asset.hosting_notifications(
            tenant_id, workspace_id, target, status, created_at DESC
          );

        CREATE TABLE digital_asset.compute_usage_events (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          asset_id uuid NOT NULL,
          deployment_id uuid,
          hosting_mode text NOT NULL
            CHECK (hosting_mode IN ('cloud', 'terminal')),
          compute_node text NOT NULL
            CHECK (compute_node IN ('warehouse', 'vultr', 'mac_mini', 'user_terminal')),
          cpu_seconds numeric(20,6) NOT NULL DEFAULT 0 CHECK (cpu_seconds >= 0),
          memory_mb_seconds numeric(24,6) NOT NULL DEFAULT 0
            CHECK (memory_mb_seconds >= 0),
          gpu_seconds numeric(20,6) NOT NULL DEFAULT 0 CHECK (gpu_seconds >= 0),
          network_bytes bigint NOT NULL DEFAULT 0 CHECK (network_bytes >= 0),
          estimated_cost_cny numeric(20,6) NOT NULL DEFAULT 0
            CHECK (estimated_cost_cny >= 0),
          billing_status text NOT NULL DEFAULT 'metered'
            CHECK (billing_status IN ('not_billable', 'metered', 'invoiced', 'void')),
          metering_source text NOT NULL DEFAULT 'runtime'
            CHECK (metering_source IN ('runtime', 'terminal', 'operator', 'system')),
          idempotency_key text,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(metadata) = 'object'),
          started_at timestamptz,
          completed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, asset_id)
            REFERENCES digital_asset.assets(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, deployment_id)
            REFERENCES digital_asset.deployments(tenant_id, id) ON DELETE SET NULL
        );
        CREATE UNIQUE INDEX uq_compute_usage_idempotency
          ON digital_asset.compute_usage_events(tenant_id, idempotency_key)
          WHERE idempotency_key IS NOT NULL;
        CREATE INDEX idx_compute_usage_workspace_created
          ON digital_asset.compute_usage_events(tenant_id, workspace_id, created_at DESC);

        GRANT SELECT, INSERT, UPDATE, DELETE
          ON digital_asset.hosting_notifications,
             digital_asset.compute_usage_events
          TO warehouse_os;

        ALTER TABLE digital_asset.hosting_notifications ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.hosting_notifications FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.hosting_notifications
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE digital_asset.compute_usage_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.compute_usage_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.compute_usage_events
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        COMMENT ON COLUMN digital_asset.workspaces.hosting_mode IS
          'User-selected execution mode: cloud keeps the existing server Runtime; terminal delegates execution to a paired user device or AI.';
        COMMENT ON COLUMN digital_asset.workspaces.compute_node IS
          'Cloud compute provider when hosting_mode=cloud; user_terminal is the terminal mode provider.';
        COMMENT ON TABLE digital_asset.hosting_notifications IS
          'Tenant-isolated reminders delivered to a paired user terminal or AI connector.';
        COMMENT ON TABLE digital_asset.compute_usage_events IS
          'Append-only resource ledger for future cloud-compute billing, separate from storage hosting usage.';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS digital_asset.compute_usage_events;
        DROP TABLE IF EXISTS digital_asset.hosting_notifications;
        DROP INDEX IF EXISTS digital_asset.idx_digital_asset_workspaces_hosting_mode;
        ALTER TABLE digital_asset.workspaces
          DROP COLUMN IF EXISTS compute_node,
          DROP COLUMN IF EXISTS hosting_mode;
        """
    )
