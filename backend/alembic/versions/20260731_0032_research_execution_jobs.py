"""Add durable, tenant-isolated research execution jobs.

Revision ID: 20260731_0032
Revises: 20260731_0031
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "20260731_0032"
down_revision = "20260731_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE research.execution_jobs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          run_id uuid,
          parent_job_id uuid,
          job_code text NOT NULL,
          title text NOT NULL CHECK (length(trim(title)) > 0),
          runtime text NOT NULL CHECK (runtime IN ('python-3.13')),
          entrypoint text NOT NULL CHECK (
            length(entrypoint) BETWEEN 1 AND 500
            AND entrypoint !~ '(^/|(^|/)\\.\\.(/|$))'
          ),
          arguments jsonb NOT NULL DEFAULT '[]'::jsonb
            CHECK (jsonb_typeof(arguments) = 'array'),
          status text NOT NULL DEFAULT 'queued' CHECK (status IN (
            'queued', 'preparing', 'running', 'succeeded', 'failed',
            'cancelled', 'timed_out'
          )),
          input_manifest jsonb NOT NULL,
          manifest_sha256 char(64) NOT NULL
            CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
          resource_limits jsonb NOT NULL DEFAULT '{}'::jsonb,
          result_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
          stdout_excerpt text NOT NULL DEFAULT '',
          stderr_excerpt text NOT NULL DEFAULT '',
          exit_code integer,
          requested_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          claimed_by text,
          claimed_at timestamptz,
          heartbeat_at timestamptz,
          started_at timestamptz,
          finished_at timestamptz,
          cancel_requested_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, job_code),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id)
            REFERENCES research.projects(tenant_id, id) ON DELETE CASCADE,
          CONSTRAINT fk_research_execution_run
          FOREIGN KEY (tenant_id, project_id, run_id)
            REFERENCES research.runs(tenant_id, project_id, id)
            ON DELETE SET NULL (run_id),
          CONSTRAINT fk_research_execution_parent
          FOREIGN KEY (tenant_id, project_id, parent_job_id)
            REFERENCES research.execution_jobs(tenant_id, project_id, id)
            ON DELETE SET NULL (parent_job_id)
        );
        CREATE INDEX idx_research_execution_queue
          ON research.execution_jobs(status, created_at)
          WHERE status IN ('queued', 'preparing', 'running');
        CREATE INDEX idx_research_execution_project
          ON research.execution_jobs(tenant_id, project_id, created_at DESC);

        CREATE TABLE research.execution_events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          job_id uuid NOT NULL,
          event_type text NOT NULL,
          message text NOT NULL DEFAULT '',
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (tenant_id, project_id, job_id)
            REFERENCES research.execution_jobs(tenant_id, project_id, id)
            ON DELETE CASCADE
        );
        CREATE INDEX idx_research_execution_events
          ON research.execution_events(tenant_id, project_id, job_id, id);

        CREATE TABLE research.execution_artifacts (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          project_id uuid NOT NULL,
          job_id uuid NOT NULL,
          relative_path text NOT NULL CHECK (
            length(relative_path) BETWEEN 1 AND 500
            AND relative_path !~ '(^/|(^|/)\\.\\.(/|$))'
          ),
          content_type text NOT NULL DEFAULT 'application/octet-stream',
          content_sha256 char(64) NOT NULL
            CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
          size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
          promoted_file_version_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, project_id, job_id, relative_path),
          UNIQUE (tenant_id, project_id, id),
          FOREIGN KEY (tenant_id, project_id, job_id)
            REFERENCES research.execution_jobs(tenant_id, project_id, id)
            ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, project_id, promoted_file_version_id)
            REFERENCES research.file_versions(tenant_id, project_id, id)
            ON DELETE SET NULL (promoted_file_version_id)
        );
        CREATE INDEX idx_research_execution_artifacts
          ON research.execution_artifacts(tenant_id, project_id, job_id, created_at);

        CREATE TRIGGER trg_research_execution_jobs_updated
          BEFORE UPDATE ON research.execution_jobs
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'research.execution_jobs', 'research.execution_events',
            'research.execution_artifacts'
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

        CREATE OR REPLACE FUNCTION app.claim_next_research_execution(
          p_worker_id text
        ) RETURNS TABLE(job_id uuid, tenant_id uuid)
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public, research
        AS $$
        DECLARE
          tenant_record record;
          claimed_record record;
        BEGIN
          FOR tenant_record IN SELECT id FROM iam.tenants WHERE status = 'active' LOOP
            PERFORM set_config('app.tenant_id', tenant_record.id::text, true);
            claimed_record := NULL;
            WITH candidate AS (
              SELECT queued.id
              FROM research.execution_jobs AS queued
              WHERE queued.status = 'queued'
                 OR (
                   queued.status IN ('preparing', 'running')
                   AND queued.heartbeat_at < now() - interval '5 minutes'
                 )
              ORDER BY queued.created_at
              FOR UPDATE SKIP LOCKED
              LIMIT 1
            )
            UPDATE research.execution_jobs AS claimed
            SET status = 'preparing', claimed_by = p_worker_id,
                claimed_at = now(), heartbeat_at = now(),
                stdout_excerpt = CASE
                  WHEN claimed.status = 'queued' THEN claimed.stdout_excerpt
                  ELSE claimed.stdout_excerpt || E'\\n[worker recovered stale lease]'
                END
            FROM candidate
            WHERE claimed.id = candidate.id
            RETURNING claimed.id, claimed.tenant_id INTO claimed_record;
            IF claimed_record.id IS NOT NULL THEN
              job_id := claimed_record.id;
              tenant_id := claimed_record.tenant_id;
              RETURN NEXT;
              RETURN;
            END IF;
          END LOOP;
          RETURN;
        END;
        $$;
        REVOKE ALL ON FUNCTION app.claim_next_research_execution(text) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION app.claim_next_research_execution(text) TO warehouse_os;

        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA research
          TO warehouse_os;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA research TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP FUNCTION IF EXISTS app.claim_next_research_execution(text);
        DROP TABLE IF EXISTS research.execution_artifacts;
        DROP TABLE IF EXISTS research.execution_events;
        DROP TABLE IF EXISTS research.execution_jobs;
        """
    )
