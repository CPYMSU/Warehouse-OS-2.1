"""Add tenant-isolated, verifiable attachments to every workflow node.

Revision ID: 20260730_0026
Revises: 20260730_0025
Create Date: 2026-07-30
"""

from __future__ import annotations

from alembic import op

revision = "20260730_0026"
down_revision = "20260730_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE compatibility.blobs
          ADD CONSTRAINT uq_compatibility_blobs_tenant_id_id
          UNIQUE (tenant_id, id);

        CREATE TABLE workflow.node_attachments (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          instance_id uuid NOT NULL,
          node_key text NOT NULL,
          attachment_key uuid NOT NULL,
          kind text NOT NULL DEFAULT 'node_attachment',
          version integer NOT NULL DEFAULT 1 CHECK (version > 0),
          blob_id uuid NOT NULL,
          file_name text NOT NULL,
          content_type text NOT NULL,
          size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
          content_sha256 char(64) NOT NULL
            CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
          previous_event_hash char(64)
            CHECK (previous_event_hash IS NULL OR previous_event_hash ~ '^[0-9a-f]{64}$'),
          event_hash char(64) NOT NULL
            CHECK (event_hash ~ '^[0-9a-f]{64}$'),
          notary_serial text NOT NULL,
          notary_signature char(64) NOT NULL
            CHECK (notary_signature ~ '^[0-9a-f]{64}$'),
          uploaded_by uuid NOT NULL REFERENCES iam.users(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL,
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, instance_id, node_key, attachment_key, version),
          UNIQUE (tenant_id, notary_serial),
          UNIQUE (tenant_id, event_hash),
          FOREIGN KEY (tenant_id, instance_id)
            REFERENCES workflow.instances(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, blob_id)
            REFERENCES compatibility.blobs(tenant_id, id) ON DELETE RESTRICT
        );

        CREATE INDEX idx_workflow_node_attachments_instance
          ON workflow.node_attachments(
            tenant_id, instance_id, node_key, created_at DESC
          );

        ALTER TABLE workflow.node_attachments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE workflow.node_attachments FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON workflow.node_attachments
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT SELECT, INSERT, UPDATE, DELETE
          ON workflow.node_attachments TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS workflow.node_attachments;
        ALTER TABLE compatibility.blobs
          DROP CONSTRAINT IF EXISTS uq_compatibility_blobs_tenant_id_id;
        """
    )
