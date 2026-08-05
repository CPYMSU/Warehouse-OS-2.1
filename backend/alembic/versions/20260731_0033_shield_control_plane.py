"""Add the tenant-scoped SHIELD telemetry, incident and audit control plane.

Revision ID: 20260731_0033
Revises: 20260731_0032
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op

revision = "20260731_0033"
down_revision = "20260731_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE SCHEMA IF NOT EXISTS shield;

        CREATE TABLE shield.snapshots (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          sampled_at timestamptz NOT NULL,
          state text NOT NULL CHECK (
            state IN (
              'healthy', 'watch', 'degraded', 'capacity-risk',
              'runtime-flapping', 'incident', 'integrity-alert',
              'under-attack', 'offline'
            )
          ),
          severity smallint NOT NULL CHECK (severity BETWEEN 0 AND 5),
          health_score smallint CHECK (health_score BETWEEN 0 AND 100),
          source text NOT NULL DEFAULT 'warehouse-shield-agent',
          payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, sampled_at),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_shield_snapshots_tenant_sampled
          ON shield.snapshots(tenant_id, sampled_at DESC);

        CREATE TABLE shield.incidents (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          signature text NOT NULL CHECK (length(trim(signature)) > 0),
          title text NOT NULL CHECK (length(trim(title)) > 0),
          source text NOT NULL DEFAULT 'warehouse-shield-agent',
          severity smallint NOT NULL CHECK (severity BETWEEN 1 AND 5),
          state text NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'resolved')),
          details jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details) = 'object'),
          opened_at timestamptz NOT NULL DEFAULT now(),
          last_seen_at timestamptz NOT NULL DEFAULT now(),
          resolved_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id)
        );
        CREATE UNIQUE INDEX uq_shield_incidents_open_signature
          ON shield.incidents(tenant_id, signature) WHERE state = 'open';
        CREATE INDEX idx_shield_incidents_tenant_state
          ON shield.incidents(tenant_id, state, last_seen_at DESC);

        CREATE TABLE shield.repair_runs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          action text NOT NULL CHECK (
            action IN (
              'healthcheck', 'restart-api', 'restart-firefighter',
              'reload-nginx', 'restart-nginx', 'clear-health-flag'
            )
          ),
          confirmation_received boolean NOT NULL DEFAULT false,
          apply_requested boolean NOT NULL DEFAULT false,
          applied boolean NOT NULL DEFAULT false,
          status text NOT NULL CHECK (
            status IN ('running', 'scheduled', 'succeeded', 'failed')
          ),
          request_id text NOT NULL CHECK (length(trim(request_id)) > 0),
          request jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(request) = 'object'),
          result jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(result) = 'object'),
          error text,
          started_at timestamptz NOT NULL DEFAULT now(),
          completed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          UNIQUE (tenant_id, request_id)
        );
        CREATE INDEX idx_shield_repairs_tenant_created
          ON shield.repair_runs(tenant_id, created_at DESC);

        CREATE TABLE shield.ai_risk_reviews (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          execution_id uuid NOT NULL,
          state text NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'reviewed', 'dismissed')),
          risk text NOT NULL DEFAULT 'high',
          summary jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(summary) = 'object'),
          reviewed_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          reviewed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, execution_id),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_shield_risks_tenant_state
          ON shield.ai_risk_reviews(tenant_id, state, created_at DESC);

        CREATE TABLE shield.audit_chain (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE RESTRICT,
          actor_user_id uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          event_type text NOT NULL CHECK (event_type ~ '^[a-z][a-z0-9_.-]{2,127}$'),
          payload jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
          previous_hash text,
          event_hash text NOT NULL UNIQUE CHECK (event_hash ~ '^[a-f0-9]{64}$'),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_shield_audit_tenant_created
          ON shield.audit_chain(tenant_id, created_at DESC);

        CREATE OR REPLACE FUNCTION shield.reject_audit_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'shield audit chain is append-only';
        END;
        $$;
        CREATE TRIGGER trg_shield_audit_append_only
          BEFORE UPDATE OR DELETE ON shield.audit_chain
          FOR EACH ROW EXECUTE FUNCTION shield.reject_audit_mutation();

        CREATE OR REPLACE FUNCTION shield.append_audit(
          p_tenant_id uuid,
          p_actor_user_id uuid,
          p_event_type text,
          p_payload jsonb
        ) RETURNS bigint
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public, app, shield
        AS $$
        DECLARE
          v_previous text;
          v_hash text;
          v_id bigint;
          v_created_at timestamptz := clock_timestamp();
        BEGIN
          IF p_tenant_id IS DISTINCT FROM app.current_tenant_id() THEN
            RAISE EXCEPTION 'shield tenant scope mismatch';
          END IF;
          IF p_event_type !~ '^[a-z][a-z0-9_.-]{2,127}$' THEN
            RAISE EXCEPTION 'invalid shield event type';
          END IF;
          PERFORM pg_advisory_xact_lock(hashtextextended(p_tenant_id::text, 734321));
          SELECT event_hash INTO v_previous
          FROM shield.audit_chain
          WHERE tenant_id = p_tenant_id
          ORDER BY id DESC
          LIMIT 1;
          v_hash := encode(
            digest(
              concat_ws(
                '|', COALESCE(v_previous, ''), p_tenant_id::text,
                COALESCE(p_actor_user_id::text, ''), p_event_type,
                COALESCE(p_payload, '{}'::jsonb)::text, v_created_at::text
              ),
              'sha256'
            ),
            'hex'
          );
          INSERT INTO shield.audit_chain(
            tenant_id, actor_user_id, event_type, payload,
            previous_hash, event_hash, created_at
          ) VALUES (
            p_tenant_id, p_actor_user_id, p_event_type,
            COALESCE(p_payload, '{}'::jsonb), v_previous, v_hash, v_created_at
          ) RETURNING id INTO v_id;
          RETURN v_id;
        END;
        $$;

        CREATE TRIGGER trg_shield_incidents_updated
          BEFORE UPDATE ON shield.incidents
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_shield_risks_updated
          BEFORE UPDATE ON shield.ai_risk_reviews
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE shield.snapshots ENABLE ROW LEVEL SECURITY;
        ALTER TABLE shield.snapshots FORCE ROW LEVEL SECURITY;
        ALTER TABLE shield.incidents ENABLE ROW LEVEL SECURITY;
        ALTER TABLE shield.incidents FORCE ROW LEVEL SECURITY;
        ALTER TABLE shield.repair_runs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE shield.repair_runs FORCE ROW LEVEL SECURITY;
        ALTER TABLE shield.ai_risk_reviews ENABLE ROW LEVEL SECURITY;
        ALTER TABLE shield.ai_risk_reviews FORCE ROW LEVEL SECURITY;
        ALTER TABLE shield.audit_chain ENABLE ROW LEVEL SECURITY;
        ALTER TABLE shield.audit_chain FORCE ROW LEVEL SECURITY;

        CREATE POLICY tenant_isolation ON shield.snapshots
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        CREATE POLICY tenant_isolation ON shield.incidents
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        CREATE POLICY tenant_isolation ON shield.repair_runs
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        CREATE POLICY tenant_isolation ON shield.ai_risk_reviews
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        CREATE POLICY tenant_isolation ON shield.audit_chain
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT USAGE ON SCHEMA shield TO warehouse_os;
        GRANT SELECT, INSERT ON shield.snapshots TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON shield.incidents TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON shield.repair_runs TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON shield.ai_risk_reviews TO warehouse_os;
        GRANT SELECT ON shield.audit_chain TO warehouse_os;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA shield TO warehouse_os;
        GRANT EXECUTE ON FUNCTION shield.append_audit(uuid, uuid, text, jsonb)
          TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA shield
          GRANT SELECT, INSERT, UPDATE ON TABLES TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA shield
          GRANT USAGE, SELECT ON SEQUENCES TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS shield CASCADE")
