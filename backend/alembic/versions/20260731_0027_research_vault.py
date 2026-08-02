"""Add the tenant-isolated research vault and Git-backed revision index.

Revision ID: 20260731_0027
Revises: 20260730_0026
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "20260731_0027"
down_revision = "20260730_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS research;

        CREATE TABLE research.projects (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          slug text NOT NULL CHECK (slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
          title text NOT NULL CHECK (length(trim(title)) > 0),
          summary text,
          research_area text,
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('draft', 'active', 'review', 'published', 'archived')),
          default_branch text NOT NULL DEFAULT 'main'
            CHECK (default_branch ~ '^[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$'),
          head_git_sha text
            CHECK (head_git_sha IS NULL OR head_git_sha ~ '^[0-9a-f]{40}([0-9a-f]{24})?$'),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, slug),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_research_projects_tenant_updated
          ON research.projects(tenant_id, updated_at DESC);

        CREATE TABLE research.files (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          logical_path text NOT NULL CHECK (
            length(logical_path) BETWEEN 1 AND 500
            AND logical_path !~ '(^/|(^|/)\\.\\.(/|$))'
          ),
          display_name text NOT NULL CHECK (length(trim(display_name)) > 0),
          file_kind text NOT NULL CHECK (file_kind IN (
            'document', 'pdf', 'html', 'dataset', 'database', 'code',
            'notebook', 'image', 'binary'
          )),
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'superseded', 'archived')),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, logical_path),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_files_project_path
          ON research.files(tenant_id, project_id, logical_path);

        CREATE TABLE research.file_versions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          file_id uuid NOT NULL,
          version integer NOT NULL CHECK (version > 0),
          original_filename text NOT NULL,
          content_type text NOT NULL DEFAULT 'application/octet-stream',
          storage_provider text NOT NULL,
          object_key text NOT NULL,
          content_sha256 char(64) NOT NULL
            CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
          size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
          extracted_text text,
          preview jsonb NOT NULL DEFAULT '{}'::jsonb,
          git_sha text
            CHECK (git_sha IS NULL OR git_sha ~ '^[0-9a-f]{40}([0-9a-f]{24})?$'),
          commit_message text,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, file_id, version),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id, file_id)
            REFERENCES research.files(tenant_id, project_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_file_versions_latest
          ON research.file_versions(tenant_id, file_id, version DESC);
        CREATE INDEX idx_research_file_versions_git
          ON research.file_versions(tenant_id, project_id, git_sha);

        CREATE TABLE research.commits (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          git_sha text NOT NULL
            CHECK (git_sha ~ '^[0-9a-f]{40}([0-9a-f]{24})?$'),
          parent_git_sha text
            CHECK (parent_git_sha IS NULL OR parent_git_sha ~ '^[0-9a-f]{40}([0-9a-f]{24})?$'),
          branch_name text NOT NULL,
          message text NOT NULL CHECK (length(trim(message)) > 0),
          manifest jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, git_sha),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_commits_project_time
          ON research.commits(tenant_id, project_id, created_at DESC);

        CREATE TABLE research.provenance_edges (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          source_version_id uuid NOT NULL,
          target_version_id uuid NOT NULL,
          relation text NOT NULL CHECK (relation IN (
            'derived_from', 'generated_by', 'uses_data', 'uses_code', 'documents'
          )),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CHECK (source_version_id <> target_version_id),
          FOREIGN KEY (tenant_id, project_id, source_version_id)
            REFERENCES research.file_versions(tenant_id, project_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, project_id, target_version_id)
            REFERENCES research.file_versions(tenant_id, project_id, id) ON DELETE CASCADE
        );

        CREATE TRIGGER trg_research_projects_updated
          BEFORE UPDATE ON research.projects
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_research_files_updated
          BEFORE UPDATE ON research.files
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'research.projects', 'research.files', 'research.file_versions',
            'research.commits', 'research.provenance_edges'
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

        GRANT USAGE ON SCHEMA research TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA research TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA research
          GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;

        UPDATE iam.position_profiles
        SET permissions = permissions || '["research.read"]'::jsonb
        WHERE position_code IN (
          'research_center_director', 'research_center_deputy_director',
          'principal_investigator', 'researcher', 'research_assistant',
          'scientific_research_center_director',
          'scientific_research_center_deputy_director',
          'research_technology_manager', 'lab_research_engineer',
          'technical_researcher'
        ) AND NOT permissions ? 'research.read';

        UPDATE iam.position_profiles
        SET permissions = permissions || '["research.write"]'::jsonb
        WHERE position_code IN (
          'research_center_director', 'research_center_deputy_director',
          'principal_investigator', 'researcher', 'research_assistant',
          'scientific_research_center_director',
          'scientific_research_center_deputy_director',
          'research_technology_manager', 'lab_research_engineer',
          'technical_researcher'
        ) AND NOT permissions ? 'research.write';

        UPDATE iam.position_profiles
        SET permissions = permissions || '["research.review"]'::jsonb
        WHERE position_code IN (
          'research_center_director', 'research_center_deputy_director',
          'principal_investigator', 'scientific_research_center_director',
          'scientific_research_center_deputy_director',
          'research_technology_manager'
        ) AND NOT permissions ? 'research.review';
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS research CASCADE")
