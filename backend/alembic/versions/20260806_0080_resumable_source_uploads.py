"""Add resumable asynchronous workspace source uploads.

Revision ID: 20260806_0080
Revises: 20260806_0079
"""

from __future__ import annotations

from alembic import op

revision = "20260806_0080"
down_revision = "20260806_0079"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE digital_asset.source_upload_jobs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          workspace_id uuid NOT NULL,
          credential_id uuid NOT NULL,
          idempotency_key text NOT NULL
            CHECK (length(trim(idempotency_key)) BETWEEN 8 AND 240),
          request_digest text NOT NULL CHECK (request_digest ~ '^[a-f0-9]{64}$'),
          filename text NOT NULL CHECK (length(trim(filename)) BETWEEN 1 AND 240),
          content_type text,
          version_no text CHECK (
            version_no IS NULL OR length(trim(version_no)) BETWEEN 1 AND 80
          ),
          component_name text,
          expected_size_bytes bigint NOT NULL CHECK (expected_size_bytes > 0),
          expected_sha256 text NOT NULL CHECK (expected_sha256 ~ '^[a-f0-9]{64}$'),
          chunk_size_bytes integer NOT NULL CHECK (chunk_size_bytes > 0),
          part_count integer NOT NULL CHECK (part_count > 0),
          received_bytes bigint NOT NULL DEFAULT 0 CHECK (received_bytes >= 0),
          received_parts integer NOT NULL DEFAULT 0 CHECK (received_parts >= 0),
          status text NOT NULL DEFAULT 'created' CHECK (status IN (
            'created','uploading','queued','verifying','verified',
            'failed','expired','cancelled'
          )),
          attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
          lease_owner text,
          lease_expires_at timestamptz,
          storage_provider text NOT NULL,
          source_version_id uuid,
          result jsonb NOT NULL DEFAULT '{}'::jsonb,
          error jsonb NOT NULL DEFAULT '{}'::jsonb,
          expires_at timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
          completed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, workspace_id, idempotency_key),
          FOREIGN KEY (tenant_id, workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id, id),
          FOREIGN KEY (tenant_id, credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id, id),
          FOREIGN KEY (tenant_id, source_version_id)
            REFERENCES digital_asset.asset_versions(tenant_id, id)
        );

        CREATE TABLE digital_asset.source_upload_parts (
          upload_id uuid NOT NULL,
          tenant_id uuid NOT NULL,
          part_no integer NOT NULL CHECK (part_no >= 0),
          size_bytes integer NOT NULL CHECK (size_bytes > 0),
          sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (upload_id, part_no),
          FOREIGN KEY (tenant_id, upload_id)
            REFERENCES digital_asset.source_upload_jobs(tenant_id, id)
        );

        CREATE UNIQUE INDEX uq_source_upload_active_version
          ON digital_asset.source_upload_jobs(tenant_id, workspace_id, version_no)
          WHERE version_no IS NOT NULL
            AND status IN ('created','uploading','queued','verifying');
        CREATE INDEX idx_source_upload_queue
          ON digital_asset.source_upload_jobs(status, lease_expires_at, created_at)
          WHERE status IN ('queued','verifying');
        CREATE INDEX idx_source_upload_expiry
          ON digital_asset.source_upload_jobs(expires_at)
          WHERE status IN ('created','uploading','failed','expired','cancelled');

        ALTER TABLE digital_asset.source_upload_jobs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.source_upload_jobs FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.source_upload_jobs
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE digital_asset.source_upload_parts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.source_upload_parts FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.source_upload_parts
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT ALL PRIVILEGES
          ON digital_asset.source_upload_jobs, digital_asset.source_upload_parts
          TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS digital_asset.source_upload_parts;
        DROP TABLE IF EXISTS digital_asset.source_upload_jobs;
        """
    )
