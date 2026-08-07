"""Add semantic manuscript artifacts and parallel reviewer threads.

Revision ID: 20260807_0081
Revises: 20260806_0080
"""

from __future__ import annotations

from alembic import op

revision = "20260807_0081"
down_revision = "20260806_0080"
branch_labels = None
depends_on = None
warehouse_scope = "schema"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE research.manuscript_ai_runs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          draft_id uuid NOT NULL,
          source_revision bigint NOT NULL CHECK (source_revision >= 0),
          modes jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(modes) = 'array'),
          block_ids jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(block_ids) = 'array'),
          status text NOT NULL DEFAULT 'queued'
            CHECK (status IN ('queued', 'processing', 'ready', 'failed', 'cancelled')),
          result jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(result) = 'object'),
          error text,
          requested_by uuid,
          started_at timestamptz,
          finished_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_research_manuscript_ai_runs_draft
          ON research.manuscript_ai_runs(tenant_id, draft_id, created_at DESC);
        CREATE INDEX idx_research_manuscript_ai_runs_active
          ON research.manuscript_ai_runs(status, created_at)
          WHERE status IN ('queued', 'processing');

        CREATE TABLE research.manuscript_artifacts (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          draft_id uuid NOT NULL,
          block_id text NOT NULL CHECK (length(block_id) BETWEEN 1 AND 180),
          artifact_kind text NOT NULL CHECK (artifact_kind IN (
            'block_semantics', 'section_digest', 'document_digest',
            'formula_semantics', 'figure_semantics', 'table_semantics'
          )),
          locale text NOT NULL DEFAULT 'zh-CN' CHECK (length(locale) BETWEEN 2 AND 20),
          source_sha256 char(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
          source_revision bigint NOT NULL CHECK (source_revision >= 0),
          content jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(content) = 'object'),
          model text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (
            tenant_id, draft_id, block_id, artifact_kind, source_sha256, locale
          )
        );
        CREATE INDEX idx_research_manuscript_artifacts_current
          ON research.manuscript_artifacts(
            tenant_id, draft_id, block_id, artifact_kind, updated_at DESC
          );

        CREATE TABLE research.manuscript_agent_threads (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          draft_id uuid NOT NULL,
          agent_type text NOT NULL CHECK (agent_type IN (
            'neutrality', 'logic', 'clarity', 'professional', 'chief'
          )),
          title text NOT NULL,
          scope jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(scope) = 'object'),
          status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
          created_by uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, draft_id, agent_type)
        );

        CREATE TABLE research.manuscript_agent_messages (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          draft_id uuid NOT NULL,
          thread_id uuid NOT NULL,
          role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
          body text NOT NULL CHECK (length(trim(body)) BETWEEN 1 AND 30000),
          citations jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(citations) = 'array'),
          context_revision bigint NOT NULL CHECK (context_revision >= 0),
          model text,
          created_by uuid,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_research_manuscript_agent_messages_thread
          ON research.manuscript_agent_messages(tenant_id, thread_id, created_at);

        CREATE TABLE research.manuscript_findings (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          draft_id uuid NOT NULL,
          thread_id uuid NOT NULL,
          run_id uuid,
          agent_type text NOT NULL CHECK (agent_type IN (
            'neutrality', 'logic', 'clarity', 'professional', 'chief'
          )),
          block_id text NOT NULL CHECK (length(block_id) BETWEEN 1 AND 180),
          source_sha256 char(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
          base_revision bigint NOT NULL CHECK (base_revision >= 0),
          severity text NOT NULL DEFAULT 'medium'
            CHECK (severity IN ('low', 'medium', 'high')),
          category text NOT NULL DEFAULT '',
          quote text NOT NULL DEFAULT '',
          rationale text NOT NULL,
          suggestion text NOT NULL DEFAULT '',
          evidence jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(evidence) = 'array'),
          confidence numeric(4,3) CHECK (confidence BETWEEN 0 AND 1),
          status text NOT NULL DEFAULT 'open'
            CHECK (status IN ('open', 'accepted', 'rejected', 'stale')),
          resolved_by uuid,
          resolved_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_research_manuscript_findings_draft
          ON research.manuscript_findings(
            tenant_id, draft_id, status, agent_type, created_at DESC
          );

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'research.manuscript_ai_runs', 'research.manuscript_artifacts',
            'research.manuscript_agent_threads', 'research.manuscript_agent_messages',
            'research.manuscript_findings'
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

        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA research TO warehouse_os;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA research TO warehouse_os;
        """
    )
    op.create_foreign_key(
        "fk_manuscript_ai_runs_draft",
        "manuscript_ai_runs",
        "manuscript_drafts",
        ["draft_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_manuscript_ai_runs_requester",
        "manuscript_ai_runs",
        "users",
        ["requested_by"],
        ["id"],
        source_schema="research",
        referent_schema="iam",
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_manuscript_artifacts_draft",
        "manuscript_artifacts",
        "manuscript_drafts",
        ["draft_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_manuscript_agent_threads_draft",
        "manuscript_agent_threads",
        "manuscript_drafts",
        ["draft_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_manuscript_agent_threads_creator",
        "manuscript_agent_threads",
        "users",
        ["created_by"],
        ["id"],
        source_schema="research",
        referent_schema="iam",
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_manuscript_agent_messages_draft",
        "manuscript_agent_messages",
        "manuscript_drafts",
        ["draft_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_manuscript_agent_messages_thread",
        "manuscript_agent_messages",
        "manuscript_agent_threads",
        ["thread_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_manuscript_agent_messages_creator",
        "manuscript_agent_messages",
        "users",
        ["created_by"],
        ["id"],
        source_schema="research",
        referent_schema="iam",
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_manuscript_findings_draft",
        "manuscript_findings",
        "manuscript_drafts",
        ["draft_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_manuscript_findings_thread",
        "manuscript_findings",
        "manuscript_agent_threads",
        ["thread_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_manuscript_findings_run",
        "manuscript_findings",
        "manuscript_ai_runs",
        ["run_id"],
        ["id"],
        source_schema="research",
        referent_schema="research",
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_manuscript_findings_resolver",
        "manuscript_findings",
        "users",
        ["resolved_by"],
        ["id"],
        source_schema="research",
        referent_schema="iam",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS research.manuscript_findings;
        DROP TABLE IF EXISTS research.manuscript_agent_messages;
        DROP TABLE IF EXISTS research.manuscript_agent_threads;
        DROP TABLE IF EXISTS research.manuscript_artifacts;
        DROP TABLE IF EXISTS research.manuscript_ai_runs;
        """
    )
