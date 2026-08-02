"""Add the evidence-led research operating model.

Revision ID: 20260731_0030
Revises: 20260731_0029
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "20260731_0030"
down_revision = "20260731_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE research.dmp_revisions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          version integer NOT NULL CHECK (version > 0),
          status text NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'approved', 'superseded')),
          content jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, version),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_dmp_current
          ON research.dmp_revisions(tenant_id, project_id, version DESC);

        CREATE TABLE research.protocols (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          protocol_code text NOT NULL,
          version integer NOT NULL DEFAULT 1 CHECK (version > 0),
          title text NOT NULL CHECK (length(trim(title)) > 0),
          objective text,
          status text NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'locked', 'retired')),
          specification jsonb NOT NULL DEFAULT '{}'::jsonb,
          previous_protocol_id uuid,
          locked_at timestamptz,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, protocol_code, version),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE,
          CONSTRAINT fk_research_protocol_previous
          FOREIGN KEY (tenant_id, project_id, previous_protocol_id)
            REFERENCES research.protocols(tenant_id, project_id, id)
            ON DELETE SET NULL (previous_protocol_id)
        );
        CREATE INDEX idx_research_protocols_project
          ON research.protocols(tenant_id, project_id, created_at DESC);

        CREATE TABLE research.runs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          run_code text NOT NULL,
          protocol_id uuid,
          title text NOT NULL CHECK (length(trim(title)) > 0),
          status text NOT NULL DEFAULT 'planned'
            CHECK (status IN ('planned', 'running', 'completed', 'failed', 'cancelled')),
          inputs jsonb NOT NULL DEFAULT '{}'::jsonb,
          environment jsonb NOT NULL DEFAULT '{}'::jsonb,
          observations jsonb NOT NULL DEFAULT '{}'::jsonb,
          deviation_note text,
          started_at timestamptz,
          completed_at timestamptz,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, run_code),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE,
          CONSTRAINT fk_research_run_protocol
          FOREIGN KEY (tenant_id, project_id, protocol_id)
            REFERENCES research.protocols(tenant_id, project_id, id)
            ON DELETE SET NULL (protocol_id)
        );
        CREATE INDEX idx_research_runs_project_status
          ON research.runs(tenant_id, project_id, status, created_at DESC);

        CREATE TABLE research.claims (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          claim_code text NOT NULL,
          statement text NOT NULL CHECK (length(trim(statement)) > 0),
          status text NOT NULL DEFAULT 'draft'
            CHECK (status IN (
              'draft', 'submitted', 'accepted', 'changes_requested', 'rejected'
            )),
          confidence numeric(5,4)
            CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, claim_code),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_claims_project_status
          ON research.claims(tenant_id, project_id, status, created_at DESC);

        CREATE TABLE research.claim_evidence (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          claim_id uuid NOT NULL,
          file_version_id uuid,
          run_id uuid,
          relation text NOT NULL DEFAULT 'supports'
            CHECK (relation IN ('supports', 'contradicts', 'method', 'context')),
          note text,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CHECK (num_nonnulls(file_version_id, run_id) = 1),
          UNIQUE NULLS NOT DISTINCT (
            tenant_id, project_id, claim_id, file_version_id, run_id, relation
          ),
          FOREIGN KEY (tenant_id, project_id, claim_id)
            REFERENCES research.claims(tenant_id, project_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, project_id, file_version_id)
            REFERENCES research.file_versions(tenant_id, project_id, id)
            ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, project_id, run_id)
            REFERENCES research.runs(tenant_id, project_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_claim_evidence_claim
          ON research.claim_evidence(tenant_id, project_id, claim_id);

        CREATE TABLE research.reviews (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          target_type text NOT NULL
            CHECK (target_type IN ('dmp', 'protocol', 'claim', 'release')),
          target_id uuid NOT NULL,
          decision text NOT NULL
            CHECK (decision IN ('comment', 'approve', 'changes_requested', 'reject')),
          comment text NOT NULL DEFAULT '',
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          reviewer_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_reviews_target
          ON research.reviews(tenant_id, project_id, target_type, target_id, created_at DESC);

        CREATE TABLE research.reproduction_checks (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          status text NOT NULL CHECK (status IN ('passed', 'warning', 'failed')),
          manifest jsonb NOT NULL,
          findings jsonb NOT NULL DEFAULT '[]'::jsonb,
          manifest_sha256 char(64) NOT NULL
            CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
          executed_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          executed_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_reproduction_project
          ON research.reproduction_checks(tenant_id, project_id, executed_at DESC);

        CREATE TABLE research.releases (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          release_code text NOT NULL,
          version integer NOT NULL CHECK (version > 0),
          title text NOT NULL CHECK (length(trim(title)) > 0),
          description text,
          status text NOT NULL DEFAULT 'published'
            CHECK (status IN ('draft', 'published', 'withdrawn')),
          access_level text NOT NULL DEFAULT 'restricted'
            CHECK (access_level IN ('open', 'embargoed', 'restricted')),
          license text,
          embargo_until date,
          manifest jsonb NOT NULL,
          manifest_sha256 char(64) NOT NULL
            CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
          ro_crate jsonb NOT NULL,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          released_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          released_at timestamptz,
          UNIQUE (tenant_id, project_id, version),
          UNIQUE (tenant_id, project_id, release_code),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_research_releases_project
          ON research.releases(tenant_id, project_id, version DESC);

        CREATE TRIGGER trg_research_protocols_updated
          BEFORE UPDATE ON research.protocols
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_research_runs_updated
          BEFORE UPDATE ON research.runs
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_research_claims_updated
          BEFORE UPDATE ON research.claims
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'research.dmp_revisions', 'research.protocols', 'research.runs',
            'research.claims', 'research.claim_evidence', 'research.reviews',
            'research.reproduction_checks', 'research.releases'
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

        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA research
          TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA research
          GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS research.releases;
        DROP TABLE IF EXISTS research.reproduction_checks;
        DROP TABLE IF EXISTS research.reviews;
        DROP TABLE IF EXISTS research.claim_evidence;
        DROP TABLE IF EXISTS research.claims;
        DROP TABLE IF EXISTS research.runs;
        DROP TABLE IF EXISTS research.protocols;
        DROP TABLE IF EXISTS research.dmp_revisions;
        """
    )
