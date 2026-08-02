"""Add version-pinned document review, anchors, and retrieval indexes.

Revision ID: 20260731_0034
Revises: 20260731_0033
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "20260731_0034"
down_revision = "20260731_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE research.file_versions
          ADD CONSTRAINT uq_research_file_version_full_identity
          UNIQUE (tenant_id, project_id, file_id, id);

        CREATE TABLE research.document_indexes (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          file_version_id uuid NOT NULL,
          status text NOT NULL DEFAULT 'queued'
            CHECK (status IN ('queued', 'indexing', 'ready', 'failed')),
          distillation_status text NOT NULL DEFAULT 'queued'
            CHECK (distillation_status IN ('queued', 'processing', 'ready', 'failed', 'unavailable')),
          processor_version text NOT NULL,
          canonical_sha256 char(64),
          block_count integer NOT NULL DEFAULT 0 CHECK (block_count >= 0),
          character_count integer NOT NULL DEFAULT 0 CHECK (character_count >= 0),
          summary text,
          outline jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(outline) = 'array'),
          concepts jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(concepts) = 'array'),
          error text,
          indexed_at timestamptz,
          distilled_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, file_version_id),
          UNIQUE (tenant_id, project_id, file_id, file_version_id),
          FOREIGN KEY (tenant_id, project_id, file_id, file_version_id)
            REFERENCES research.file_versions(tenant_id, project_id, file_id, id)
            ON DELETE CASCADE
        );
        CREATE INDEX idx_research_document_indexes_project
          ON research.document_indexes(tenant_id, project_id, updated_at DESC);

        CREATE TABLE research.document_blocks (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          file_version_id uuid NOT NULL,
          ordinal integer NOT NULL CHECK (ordinal >= 0),
          stable_key text NOT NULL,
          block_type text NOT NULL CHECK (block_type IN (
            'title', 'heading', 'paragraph', 'list_item', 'table_row',
            'equation', 'caption', 'code', 'page'
          )),
          heading_level smallint CHECK (heading_level BETWEEN 1 AND 9),
          heading_path text[] NOT NULL DEFAULT '{}',
          content text NOT NULL,
          start_offset integer NOT NULL CHECK (start_offset >= 0),
          end_offset integer NOT NULL CHECK (end_offset >= start_offset),
          locator jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(locator) = 'object'),
          distilled_context jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(distilled_context) = 'object'),
          search_document tsvector GENERATED ALWAYS AS (
            to_tsvector('simple', coalesce(content, ''))
          ) STORED,
          embedding vector(1536),
          embedding_model text,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, file_version_id, ordinal),
          UNIQUE (tenant_id, file_version_id, stable_key),
          UNIQUE (tenant_id, project_id, file_id, file_version_id, id),
          FOREIGN KEY (tenant_id, project_id, file_id, file_version_id)
            REFERENCES research.file_versions(tenant_id, project_id, file_id, id)
            ON DELETE CASCADE
        );
        CREATE INDEX idx_research_document_blocks_lookup
          ON research.document_blocks(tenant_id, file_version_id, ordinal);
        CREATE INDEX idx_research_document_blocks_search
          ON research.document_blocks USING gin(search_document);
        CREATE INDEX idx_research_document_blocks_embedding
          ON research.document_blocks USING hnsw (embedding vector_cosine_ops)
          WHERE embedding IS NOT NULL;

        CREATE TABLE research.document_annotations (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          file_version_id uuid NOT NULL,
          anchor jsonb NOT NULL CHECK (jsonb_typeof(anchor) = 'object'),
          quote text NOT NULL CHECK (length(quote) BETWEEN 1 AND 12000),
          body text NOT NULL CHECK (length(trim(body)) BETWEEN 1 AND 20000),
          status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          resolved_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          resolved_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, file_id, file_version_id, id),
          FOREIGN KEY (tenant_id, project_id, file_id, file_version_id)
            REFERENCES research.file_versions(tenant_id, project_id, file_id, id)
            ON DELETE CASCADE
        );
        CREATE INDEX idx_research_document_annotations_version
          ON research.document_annotations(tenant_id, file_version_id, status, created_at);

        CREATE TABLE research.document_annotation_messages (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          file_version_id uuid NOT NULL,
          annotation_id uuid NOT NULL,
          message_kind text NOT NULL DEFAULT 'user'
            CHECK (message_kind IN ('user', 'ai', 'system')),
          body text NOT NULL CHECK (length(trim(body)) BETWEEN 1 AND 20000),
          citations jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(citations) = 'array'),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (tenant_id, project_id, file_id, file_version_id, annotation_id)
            REFERENCES research.document_annotations(
              tenant_id, project_id, file_id, file_version_id, id
            ) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_annotation_messages_thread
          ON research.document_annotation_messages(tenant_id, annotation_id, created_at);

        CREATE TABLE research.document_questions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          file_version_id uuid NOT NULL,
          question text NOT NULL CHECK (length(trim(question)) BETWEEN 1 AND 12000),
          selection_anchor jsonb CHECK (
            selection_anchor IS NULL OR jsonb_typeof(selection_anchor) = 'object'
          ),
          answer text NOT NULL,
          citations jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(citations) = 'array'),
          model text,
          asked_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, file_id, file_version_id, id),
          FOREIGN KEY (tenant_id, project_id, file_id, file_version_id)
            REFERENCES research.file_versions(tenant_id, project_id, file_id, id)
            ON DELETE CASCADE
        );
        CREATE INDEX idx_research_document_questions_version
          ON research.document_questions(tenant_id, file_version_id, created_at DESC);

        CREATE TRIGGER trg_research_document_indexes_updated
          BEFORE UPDATE ON research.document_indexes
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_research_document_annotations_updated
          BEFORE UPDATE ON research.document_annotations
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'research.document_indexes', 'research.document_blocks',
            'research.document_annotations', 'research.document_annotation_messages',
            'research.document_questions'
          ]
          LOOP
            EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', scoped_table);
            EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', scoped_table);
            EXECUTE format(
              'CREATE POLICY tenant_isolation ON %s '
              'USING (tenant_id = app.current_tenant_id()) '
              'WITH CHECK (tenant_id = app.current_tenant_id())',
              scoped_table
            );
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS research.document_questions;
        DROP TABLE IF EXISTS research.document_annotation_messages;
        DROP TABLE IF EXISTS research.document_annotations;
        DROP TABLE IF EXISTS research.document_blocks;
        DROP TABLE IF EXISTS research.document_indexes;
        ALTER TABLE research.file_versions
          DROP CONSTRAINT IF EXISTS uq_research_file_version_full_identity;
        """
    )
