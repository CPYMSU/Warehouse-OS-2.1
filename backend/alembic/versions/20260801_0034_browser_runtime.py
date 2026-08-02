"""Add the tenant-isolated browser execution control plane.

Revision ID: 20260801_0034
Revises: 20260731_0033
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0034"
down_revision = "20260731_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE SCHEMA IF NOT EXISTS browser_runtime;

        CREATE TABLE browser_runtime.journeys (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          journey_key text NOT NULL CHECK (journey_key ~ '^[a-z][a-z0-9._-]{2,79}$'),
          name text NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 160),
          description text NOT NULL DEFAULT '',
          mode text NOT NULL DEFAULT 'smoke' CHECK (mode IN ('smoke', 'full', 'explore')),
          auth_mode text NOT NULL DEFAULT 'actor' CHECK (auth_mode IN ('actor', 'anonymous')),
          mutation_policy text NOT NULL DEFAULT 'read_only'
            CHECK (mutation_policy IN ('read_only', 'allow_writes')),
          start_path text NOT NULL DEFAULT '/' CHECK (
            start_path LIKE '/%' AND start_path NOT LIKE '//%' AND length(start_path) <= 500
          ),
          steps jsonb NOT NULL CHECK (jsonb_typeof(steps) = 'array'),
          active boolean NOT NULL DEFAULT true,
          version integer NOT NULL DEFAULT 1 CHECK (version > 0),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, journey_key),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_browser_journeys_tenant_active
          ON browser_runtime.journeys(tenant_id, active, updated_at DESC);

        CREATE TABLE browser_runtime.runs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          journey_id uuid,
          journey_version integer,
          name text NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 160),
          mode text NOT NULL DEFAULT 'smoke' CHECK (mode IN ('smoke', 'full', 'explore')),
          auth_mode text NOT NULL DEFAULT 'actor' CHECK (auth_mode IN ('actor', 'anonymous')),
          mutation_policy text NOT NULL DEFAULT 'read_only'
            CHECK (mutation_policy IN ('read_only', 'allow_writes')),
          target_origin text NOT NULL CHECK (target_origin ~ '^https?://[^/]+$'),
          start_path text NOT NULL DEFAULT '/' CHECK (
            start_path LIKE '/%' AND start_path NOT LIKE '//%' AND length(start_path) <= 500
          ),
          browser text NOT NULL DEFAULT 'chromium' CHECK (browser IN ('chromium')),
          viewport jsonb NOT NULL DEFAULT jsonb_build_object('width', 1440, 'height', 1000)
            CHECK (jsonb_typeof(viewport) = 'object'),
          steps_manifest jsonb NOT NULL CHECK (jsonb_typeof(steps_manifest) = 'array'),
          status text NOT NULL DEFAULT 'queued' CHECK (status IN (
            'queued', 'claimed', 'running', 'succeeded', 'failed',
            'cancelled', 'timed_out'
          )),
          requested_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          claimed_by text,
          claimed_at timestamptz,
          heartbeat_at timestamptz,
          started_at timestamptz,
          finished_at timestamptz,
          cancel_requested_at timestamptz,
          current_step integer NOT NULL DEFAULT 0 CHECK (current_step >= 0),
          result_summary jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(result_summary) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          CONSTRAINT fk_browser_run_journey FOREIGN KEY (tenant_id, journey_id)
            REFERENCES browser_runtime.journeys(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_browser_runs_queue
          ON browser_runtime.runs(status, created_at)
          WHERE status IN ('queued', 'claimed', 'running');
        CREATE INDEX idx_browser_runs_tenant_created
          ON browser_runtime.runs(tenant_id, created_at DESC);

        CREATE TABLE browser_runtime.steps (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL,
          run_id uuid NOT NULL,
          ordinal integer NOT NULL CHECK (ordinal >= 1),
          action text NOT NULL CHECK (action IN (
            'navigate', 'click', 'fill', 'press', 'observe', 'wait', 'screenshot'
          )),
          status text NOT NULL DEFAULT 'pending' CHECK (status IN (
            'pending', 'running', 'succeeded', 'failed', 'blocked', 'skipped'
          )),
          request jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(request) = 'object'),
          observation jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(observation) = 'object'),
          error text,
          started_at timestamptz,
          finished_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, run_id, ordinal),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES browser_runtime.runs(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_browser_steps_run
          ON browser_runtime.steps(tenant_id, run_id, ordinal);

        CREATE TABLE browser_runtime.events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL,
          run_id uuid NOT NULL,
          step_id uuid,
          event_type text NOT NULL CHECK (event_type ~ '^[a-z][a-z0-9_.-]{2,127}$'),
          message text NOT NULL DEFAULT '',
          payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES browser_runtime.runs(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, step_id)
            REFERENCES browser_runtime.steps(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_browser_events_run
          ON browser_runtime.events(tenant_id, run_id, id);

        CREATE TABLE browser_runtime.artifacts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL,
          run_id uuid NOT NULL,
          step_id uuid,
          kind text NOT NULL CHECK (kind IN ('screenshot', 'dom', 'trace', 'console', 'network')),
          relative_path text NOT NULL CHECK (
            length(relative_path) BETWEEN 1 AND 500
            AND relative_path !~ '(^/|(^|/)\\.\\.(/|$))'
          ),
          content_type text NOT NULL,
          content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
          size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, run_id, relative_path),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, run_id)
            REFERENCES browser_runtime.runs(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, step_id)
            REFERENCES browser_runtime.steps(tenant_id, id) ON DELETE SET NULL
        );
        CREATE INDEX idx_browser_artifacts_run
          ON browser_runtime.artifacts(tenant_id, run_id, created_at);

        CREATE TABLE browser_runtime.workers (
          worker_id text PRIMARY KEY CHECK (length(worker_id) BETWEEN 3 AND 160),
          release_id text NOT NULL DEFAULT 'unknown',
          state text NOT NULL DEFAULT 'ready' CHECK (state IN ('ready', 'busy', 'stopping', 'error')),
          current_run_id uuid,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
          started_at timestamptz NOT NULL DEFAULT now(),
          last_seen_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TRIGGER trg_browser_journeys_updated
          BEFORE UPDATE ON browser_runtime.journeys
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_browser_runs_updated
          BEFORE UPDATE ON browser_runtime.runs
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'browser_runtime.journeys', 'browser_runtime.runs',
            'browser_runtime.steps', 'browser_runtime.events',
            'browser_runtime.artifacts'
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

        CREATE OR REPLACE FUNCTION app.claim_next_browser_run(p_worker_id text)
        RETURNS TABLE(run_id uuid, tenant_id uuid)
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public, app, browser_runtime
        AS $$
        DECLARE tenant_record record; claimed_record record;
        BEGIN
          IF length(trim(p_worker_id)) NOT BETWEEN 3 AND 160 THEN
            RAISE EXCEPTION 'invalid browser worker id';
          END IF;
          FOR tenant_record IN SELECT id FROM iam.tenants WHERE status = 'active' LOOP
            PERFORM set_config('app.tenant_id', tenant_record.id::text, true);
            claimed_record := NULL;
            WITH candidate AS (
              SELECT queued.id
              FROM browser_runtime.runs AS queued
              WHERE queued.status = 'queued'
                 OR (
                   queued.status IN ('claimed', 'running')
                   AND queued.heartbeat_at < now() - interval '3 minutes'
                 )
              ORDER BY queued.created_at
              FOR UPDATE SKIP LOCKED
              LIMIT 1
            )
            UPDATE browser_runtime.runs AS claimed
            SET status = 'claimed', claimed_by = p_worker_id,
                claimed_at = now(), heartbeat_at = now(),
                result_summary = CASE
                  WHEN claimed.status = 'queued' THEN claimed.result_summary
                  ELSE claimed.result_summary ||
                    jsonb_build_object('recovered_stale_lease', true)
                END
            FROM candidate
            WHERE claimed.id = candidate.id
            RETURNING claimed.id, claimed.tenant_id INTO claimed_record;
            IF claimed_record.id IS NOT NULL THEN
              run_id := claimed_record.id;
              tenant_id := claimed_record.tenant_id;
              RETURN NEXT;
              RETURN;
            END IF;
          END LOOP;
          RETURN;
        END;
        $$;

        CREATE OR REPLACE FUNCTION app.browser_run_session_actor(
          p_run_id uuid, p_worker_id text
        ) RETURNS TABLE(tenant_id uuid, actor_user_id uuid, tenant_slug text)
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public, app, browser_runtime, iam
        AS $$
        DECLARE tenant_record record; actor_record record;
        BEGIN
          FOR tenant_record IN SELECT id, slug FROM iam.tenants WHERE status = 'active' LOOP
            PERFORM set_config('app.tenant_id', tenant_record.id::text, true);
            actor_record := NULL;
            SELECT r.requested_by INTO actor_record
            FROM browser_runtime.runs r
            WHERE r.id = p_run_id
              AND r.claimed_by = p_worker_id
              AND r.status IN ('claimed', 'running')
              AND r.auth_mode = 'actor'
              AND r.requested_by IS NOT NULL
              AND r.heartbeat_at > now() - interval '3 minutes'
            LIMIT 1;
            IF actor_record.requested_by IS NOT NULL THEN
              tenant_id := tenant_record.id;
              actor_user_id := actor_record.requested_by;
              tenant_slug := tenant_record.slug;
              RETURN NEXT;
              RETURN;
            END IF;
          END LOOP;
          RETURN;
        END;
        $$;

        REVOKE ALL ON FUNCTION app.claim_next_browser_run(text) FROM PUBLIC;
        REVOKE ALL ON FUNCTION app.browser_run_session_actor(uuid, text) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION app.claim_next_browser_run(text) TO warehouse_os;
        GRANT EXECUTE ON FUNCTION app.browser_run_session_actor(uuid, text) TO warehouse_os;

        GRANT USAGE ON SCHEMA browser_runtime TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON browser_runtime.journeys TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON browser_runtime.runs TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON browser_runtime.steps TO warehouse_os;
        GRANT SELECT, INSERT ON browser_runtime.events TO warehouse_os;
        GRANT SELECT, INSERT ON browser_runtime.artifacts TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON browser_runtime.workers TO warehouse_os;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA browser_runtime TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP FUNCTION IF EXISTS app.browser_run_session_actor(uuid, text);
        DROP FUNCTION IF EXISTS app.claim_next_browser_run(text);
        DROP SCHEMA IF EXISTS browser_runtime CASCADE;
        """
    )
