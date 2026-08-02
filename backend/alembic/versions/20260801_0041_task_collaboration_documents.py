"""Add CRDT working drafts and immutable embedded-image assets.

Revision ID: 20260801_0041
Revises: 20260801_0040
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0041"
down_revision = "20260801_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE workflow.task_collaboration_documents (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          space_id uuid NOT NULL,
          document_key text NOT NULL DEFAULT 'working-draft'
            CHECK (document_key = 'working-draft'),
          title text NOT NULL DEFAULT '協作工作稿'
            CHECK (length(trim(title)) BETWEEN 1 AND 200),
          crdt_format text NOT NULL DEFAULT 'rga-v1'
            CHECK (crdt_format = 'rga-v1'),
          state text NOT NULL DEFAULT 'active'
            CHECK (state IN ('active', 'locked', 'archived')),
          latest_sequence bigint NOT NULL DEFAULT 0 CHECK (latest_sequence >= 0),
          snapshot jsonb NOT NULL DEFAULT '{"format":"rga-v1","nodes":[]}'::jsonb
            CHECK (jsonb_typeof(snapshot) = 'object'),
          snapshot_hash text NOT NULL CHECK (snapshot_hash ~ '^[0-9a-f]{64}$'),
          visible_length integer NOT NULL DEFAULT 0
            CHECK (visible_length BETWEEN 0 AND 32000),
          node_count integer NOT NULL DEFAULT 0
            CHECK (node_count BETWEEN 0 AND 50000),
          created_by_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          updated_by_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, space_id, document_key),
          FOREIGN KEY (tenant_id, space_id)
            REFERENCES workflow.task_collaboration_spaces(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_collab_documents_space
          ON workflow.task_collaboration_documents(tenant_id, space_id, id);

        CREATE TABLE workflow.task_collaboration_document_updates (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          document_id uuid NOT NULL,
          sequence bigint NOT NULL CHECK (sequence > 0),
          actor_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          client_id text NOT NULL CHECK (client_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,179}$'),
          client_update_id text NOT NULL
            CHECK (client_update_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,179}$'),
          update_payload jsonb NOT NULL CHECK (jsonb_typeof(update_payload) = 'object'),
          update_hash text NOT NULL CHECK (update_hash ~ '^[0-9a-f]{64}$'),
          byte_size integer NOT NULL CHECK (byte_size BETWEEN 2 AND 98304),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, document_id, sequence),
          UNIQUE (tenant_id, document_id, actor_user_id, client_update_id),
          FOREIGN KEY (tenant_id, document_id)
            REFERENCES workflow.task_collaboration_documents(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_collab_document_updates_cursor
          ON workflow.task_collaboration_document_updates(tenant_id, document_id, sequence);

        CREATE TABLE workflow.task_collaboration_document_snapshots (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          document_id uuid NOT NULL,
          sequence bigint NOT NULL CHECK (sequence >= 0),
          snapshot jsonb NOT NULL CHECK (jsonb_typeof(snapshot) = 'object'),
          snapshot_hash text NOT NULL CHECK (snapshot_hash ~ '^[0-9a-f]{64}$'),
          visible_length integer NOT NULL CHECK (visible_length BETWEEN 0 AND 32000),
          node_count integer NOT NULL CHECK (node_count BETWEEN 0 AND 50000),
          created_by_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, document_id, sequence),
          FOREIGN KEY (tenant_id, document_id)
            REFERENCES workflow.task_collaboration_documents(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_collab_document_snapshots_cursor
          ON workflow.task_collaboration_document_snapshots(
            tenant_id, document_id, sequence DESC
          );

        CREATE TABLE workflow.task_collaboration_document_assets (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          document_id uuid NOT NULL,
          asset_key text NOT NULL
            CHECK (asset_key ~ '^img_[A-Za-z0-9_-]{20,80}$'),
          storage_provider text NOT NULL DEFAULT 'content_addressed_local'
            CHECK (length(storage_provider) BETWEEN 1 AND 80),
          object_key text NOT NULL CHECK (length(object_key) BETWEEN 1 AND 1024),
          file_name text NOT NULL CHECK (length(file_name) BETWEEN 1 AND 255),
          alt_text text NOT NULL DEFAULT '' CHECK (length(alt_text) <= 160),
          mime_type text NOT NULL CHECK (mime_type IN ('image/jpeg', 'image/png', 'image/webp')),
          byte_size integer NOT NULL CHECK (byte_size BETWEEN 1 AND 2097152),
          width integer NOT NULL CHECK (width BETWEEN 1 AND 2048),
          height integer NOT NULL CHECK (height BETWEEN 1 AND 2048),
          sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
          created_by_user_id uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, asset_key),
          UNIQUE (tenant_id, document_id, sha256),
          FOREIGN KEY (tenant_id, document_id)
            REFERENCES workflow.task_collaboration_documents(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_collab_document_assets_document
          ON workflow.task_collaboration_document_assets(tenant_id, document_id, created_at);

        CREATE TABLE workflow.task_collaboration_presence (
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          space_id uuid NOT NULL,
          user_id uuid NOT NULL,
          client_id text NOT NULL
            CHECK (client_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$'),
          typing boolean NOT NULL DEFAULT false,
          expires_at timestamptz NOT NULL,
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, space_id, user_id, client_id),
          FOREIGN KEY (tenant_id, space_id)
            REFERENCES workflow.task_collaboration_spaces(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE
        );
        CREATE INDEX idx_task_collab_presence_expiry
          ON workflow.task_collaboration_presence(tenant_id, space_id, expires_at);

        CREATE TRIGGER trg_task_collaboration_documents_updated
          BEFORE UPDATE ON workflow.task_collaboration_documents
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        CREATE OR REPLACE FUNCTION workflow.reject_task_document_ledger_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$;
        CREATE TRIGGER trg_task_collab_document_updates_append_only
          BEFORE UPDATE OR DELETE ON workflow.task_collaboration_document_updates
          FOR EACH ROW EXECUTE FUNCTION workflow.reject_task_document_ledger_mutation();
        CREATE TRIGGER trg_task_collab_document_snapshots_append_only
          BEFORE UPDATE OR DELETE ON workflow.task_collaboration_document_snapshots
          FOR EACH ROW EXECUTE FUNCTION workflow.reject_task_document_ledger_mutation();
        CREATE TRIGGER trg_task_collab_document_assets_append_only
          BEFORE UPDATE OR DELETE ON workflow.task_collaboration_document_assets
          FOR EACH ROW EXECUTE FUNCTION workflow.reject_task_document_ledger_mutation();

        GRANT SELECT, INSERT, UPDATE ON workflow.task_collaboration_documents
          TO warehouse_os;
        GRANT SELECT, INSERT ON
          workflow.task_collaboration_document_updates,
          workflow.task_collaboration_document_snapshots,
          workflow.task_collaboration_document_assets
          TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON workflow.task_collaboration_presence
          TO warehouse_os;
        GRANT USAGE, SELECT ON SEQUENCE
          workflow.task_collaboration_document_updates_id_seq,
          workflow.task_collaboration_document_snapshots_id_seq
          TO warehouse_os;

        ALTER TABLE workflow.task_collaboration_documents ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_documents FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_documents
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_document_updates ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_document_updates FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_document_updates
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_document_snapshots ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_document_snapshots FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_document_snapshots
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_document_assets ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_document_assets FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_document_assets
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE workflow.task_collaboration_presence ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.task_collaboration_presence FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.task_collaboration_presence
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS workflow.task_collaboration_presence;
        DROP TABLE IF EXISTS workflow.task_collaboration_document_assets;
        DROP TABLE IF EXISTS workflow.task_collaboration_document_snapshots;
        DROP TABLE IF EXISTS workflow.task_collaboration_document_updates;
        DROP TABLE IF EXISTS workflow.task_collaboration_documents;
        DROP FUNCTION IF EXISTS workflow.reject_task_document_ledger_mutation();
        """
    )
