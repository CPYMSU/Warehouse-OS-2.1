"""Add tenant-isolated compatibility projections for retained frontend contracts.

Revision ID: 20260727_0010
Revises: 20260727_0009
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0010"
down_revision = "20260727_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS compatibility;

        CREATE TABLE compatibility.documents (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          namespace text NOT NULL CHECK (namespace ~ '^[a-z][a-z0-9_.-]{1,119}$'),
          document_key text NOT NULL DEFAULT 'default'
            CHECK (length(trim(document_key)) BETWEEN 1 AND 240),
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'archived')),
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          source text NOT NULL DEFAULT 'native'
            CHECK (source IN ('native', 'legacy_import', 'migration', 'manual')),
          version integer NOT NULL DEFAULT 1 CHECK (version > 0),
          updated_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, namespace, document_key),
          UNIQUE (tenant_id, id)
        );

        CREATE INDEX idx_compatibility_documents_tenant_namespace_updated
          ON compatibility.documents(tenant_id, namespace, updated_at DESC);
        CREATE INDEX idx_compatibility_documents_payload
          ON compatibility.documents USING gin(payload jsonb_path_ops);

        CREATE TRIGGER trg_compatibility_documents_updated
          BEFORE UPDATE ON compatibility.documents
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        COMMENT ON TABLE compatibility.documents IS
          'Temporary PostgreSQL read-model bridge for retained /api contracts. '
          'It stores imported or native tenant projections only; final business '
          'modules replace each namespace with explicit domain tables.';

        GRANT USAGE ON SCHEMA compatibility TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON compatibility.documents TO warehouse_os;

        ALTER TABLE compatibility.documents ENABLE ROW LEVEL SECURITY;
        ALTER TABLE compatibility.documents FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON compatibility.documents
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS compatibility.documents;
        DROP SCHEMA IF EXISTS compatibility;
        """
    )
