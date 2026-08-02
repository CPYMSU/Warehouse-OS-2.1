"""Add tenant-isolated task history and collaboration workspaces.

Revision ID: 20260801_0037
Revises: 20260801_0036
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0037"
down_revision = "20260801_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE workflow.task_events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          task_id uuid NOT NULL,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          event_type text NOT NULL CHECK (length(trim(event_type)) BETWEEN 1 AND 100),
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, task_id)
            REFERENCES workflow.tasks(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_events_task
          ON workflow.task_events(tenant_id, task_id, id DESC);

        CREATE TABLE workflow.task_collaboration_spaces (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          task_id uuid NOT NULL,
          join_policy text NOT NULL DEFAULT 'request'
            CHECK (join_policy IN ('open', 'request', 'invite_only')),
          discoverability text NOT NULL DEFAULT 'team'
            CHECK (discoverability IN ('team', 'company', 'hidden')),
          max_members integer CHECK (max_members IS NULL OR max_members BETWEEN 1 AND 500),
          created_by_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, task_id),
          FOREIGN KEY (tenant_id, task_id)
            REFERENCES workflow.tasks(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_collaboration_spaces_discover
          ON workflow.task_collaboration_spaces(tenant_id, discoverability, created_at DESC);

        CREATE TABLE workflow.task_collaboration_members (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          space_id uuid NOT NULL,
          user_id uuid NOT NULL,
          role text NOT NULL
            CHECK (role IN ('owner', 'coordinator', 'contributor', 'reviewer', 'observer')),
          state text NOT NULL DEFAULT 'active'
            CHECK (state IN ('active', 'left', 'removed')),
          joined_at timestamptz NOT NULL DEFAULT now(),
          left_at timestamptz,
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, space_id, user_id),
          FOREIGN KEY (tenant_id, space_id)
            REFERENCES workflow.task_collaboration_spaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX idx_task_collaboration_one_active_owner
          ON workflow.task_collaboration_members(tenant_id, space_id)
          WHERE state = 'active' AND role = 'owner';
        CREATE INDEX idx_task_collaboration_members_user
          ON workflow.task_collaboration_members(tenant_id, user_id, state, space_id);

        CREATE TABLE workflow.task_collaboration_join_requests (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          space_id uuid NOT NULL,
          user_id uuid NOT NULL,
          requested_role text NOT NULL DEFAULT 'contributor'
            CHECK (requested_role IN ('contributor', 'reviewer', 'observer')),
          message text CHECK (message IS NULL OR length(message) <= 1000),
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
          decided_by_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          decided_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, space_id)
            REFERENCES workflow.task_collaboration_spaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX idx_task_collaboration_one_pending_request
          ON workflow.task_collaboration_join_requests(tenant_id, space_id, user_id)
          WHERE status = 'pending';
        CREATE INDEX idx_task_collaboration_requests_space
          ON workflow.task_collaboration_join_requests(tenant_id, space_id, status, created_at);

        CREATE TABLE workflow.task_collaboration_invitations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          space_id uuid NOT NULL,
          user_id uuid NOT NULL,
          role text NOT NULL DEFAULT 'contributor'
            CHECK (role IN ('coordinator', 'contributor', 'reviewer', 'observer')),
          message text CHECK (message IS NULL OR length(message) <= 1000),
          status text NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'accepted', 'declined', 'cancelled')),
          invited_by_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          responded_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, space_id)
            REFERENCES workflow.task_collaboration_spaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX idx_task_collaboration_one_pending_invitation
          ON workflow.task_collaboration_invitations(tenant_id, space_id, user_id)
          WHERE status = 'pending';
        CREATE INDEX idx_task_collaboration_invitations_user
          ON workflow.task_collaboration_invitations(tenant_id, user_id, status, created_at DESC);

        CREATE TABLE workflow.task_collaboration_channels (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          space_id uuid NOT NULL,
          name text NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 80),
          display_name text NOT NULL CHECK (length(trim(display_name)) BETWEEN 1 AND 120),
          channel_type text NOT NULL DEFAULT 'general'
            CHECK (channel_type IN ('general', 'announcement')),
          created_by_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, space_id, name),
          FOREIGN KEY (tenant_id, space_id)
            REFERENCES workflow.task_collaboration_spaces(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_collaboration_channels_space
          ON workflow.task_collaboration_channels(tenant_id, space_id, created_at);

        CREATE TABLE workflow.task_collaboration_messages (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          channel_id uuid NOT NULL,
          sender_user_id uuid NOT NULL,
          client_message_id text NOT NULL
            CHECK (length(client_message_id) BETWEEN 1 AND 120),
          body text NOT NULL CHECK (length(trim(body)) BETWEEN 1 AND 8000),
          reply_to_message_id bigint,
          created_at timestamptz NOT NULL DEFAULT now(),
          edited_at timestamptz,
          deleted_at timestamptz,
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, channel_id, sender_user_id, client_message_id),
          FOREIGN KEY (tenant_id, channel_id)
            REFERENCES workflow.task_collaboration_channels(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, sender_user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, reply_to_message_id)
            REFERENCES workflow.task_collaboration_messages(tenant_id, id)
              ON DELETE SET NULL (reply_to_message_id)
        );
        CREATE INDEX idx_task_collaboration_messages_channel
          ON workflow.task_collaboration_messages(tenant_id, channel_id, id);

        CREATE TABLE workflow.task_collaboration_message_reads (
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          channel_id uuid NOT NULL,
          user_id uuid NOT NULL,
          last_message_id bigint,
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, channel_id, user_id),
          FOREIGN KEY (tenant_id, channel_id)
            REFERENCES workflow.task_collaboration_channels(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, last_message_id)
            REFERENCES workflow.task_collaboration_messages(tenant_id, id)
              ON DELETE SET NULL (last_message_id)
        );

        CREATE TABLE workflow.task_collaboration_events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          space_id uuid NOT NULL,
          task_id uuid NOT NULL,
          event_type text NOT NULL CHECK (length(trim(event_type)) BETWEEN 1 AND 100),
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          subject_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, space_id)
            REFERENCES workflow.task_collaboration_spaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, task_id)
            REFERENCES workflow.tasks(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_collaboration_events_space
          ON workflow.task_collaboration_events(tenant_id, space_id, id);
        CREATE INDEX idx_task_collaboration_events_task
          ON workflow.task_collaboration_events(tenant_id, task_id, id);

        CREATE TRIGGER trg_task_collaboration_spaces_updated
          BEFORE UPDATE ON workflow.task_collaboration_spaces
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_task_collaboration_members_updated
          BEFORE UPDATE ON workflow.task_collaboration_members
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_task_collaboration_requests_updated
          BEFORE UPDATE ON workflow.task_collaboration_join_requests
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_task_collaboration_invitations_updated
          BEFORE UPDATE ON workflow.task_collaboration_invitations
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        GRANT SELECT, INSERT ON workflow.task_events, workflow.task_collaboration_events
          TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON
          workflow.task_collaboration_spaces,
          workflow.task_collaboration_members,
          workflow.task_collaboration_join_requests,
          workflow.task_collaboration_invitations,
          workflow.task_collaboration_channels,
          workflow.task_collaboration_messages,
          workflow.task_collaboration_message_reads
          TO warehouse_os;
        GRANT USAGE, SELECT ON SEQUENCE
          workflow.task_events_id_seq,
          workflow.task_collaboration_messages_id_seq,
          workflow.task_collaboration_events_id_seq
          TO warehouse_os;

        ALTER TABLE workflow.task_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_events
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        ALTER TABLE workflow.task_collaboration_spaces ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_spaces FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_spaces
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_members ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_members FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_members
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_join_requests ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_join_requests FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_join_requests
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_invitations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_invitations FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_invitations
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_channels ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_channels FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_channels
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_messages ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_messages FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_messages
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_message_reads ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_message_reads FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_message_reads
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_events
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS workflow.task_collaboration_events;
        DROP TABLE IF EXISTS workflow.task_collaboration_message_reads;
        DROP TABLE IF EXISTS workflow.task_collaboration_messages;
        DROP TABLE IF EXISTS workflow.task_collaboration_channels;
        DROP TABLE IF EXISTS workflow.task_collaboration_invitations;
        DROP TABLE IF EXISTS workflow.task_collaboration_join_requests;
        DROP TABLE IF EXISTS workflow.task_collaboration_members;
        DROP TABLE IF EXISTS workflow.task_collaboration_spaces;
        DROP TABLE IF EXISTS workflow.task_events;
        """
    )
