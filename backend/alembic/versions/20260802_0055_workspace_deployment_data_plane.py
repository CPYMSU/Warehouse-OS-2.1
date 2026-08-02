"""Close the workspace source/deployment contract and add runtime leases.

Revision ID: 20260802_0055
Revises: 20260802_0054
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0055"
down_revision = "20260802_0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE platform.runtime_profiles (
          profile_key text PRIMARY KEY
            CHECK (profile_key ~ '^[a-z][a-z0-9.-]{2,63}$'),
          label text NOT NULL,
          runtime_family text NOT NULL
            CHECK (runtime_family IN ('static', 'python', 'node')),
          image_ref text,
          detector_contract jsonb NOT NULL DEFAULT '{}'::jsonb,
          execution_contract jsonb NOT NULL DEFAULT '{}'::jsonb,
          resource_limits jsonb NOT NULL DEFAULT '{}'::jsonb,
          enabled boolean NOT NULL DEFAULT true,
          revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER trg_runtime_profiles_updated
          BEFORE UPDATE ON platform.runtime_profiles
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        GRANT SELECT ON platform.runtime_profiles TO warehouse_os;

        INSERT INTO platform.runtime_profiles(
          profile_key, label, runtime_family, image_ref,
          detector_contract, execution_contract, resource_limits
        ) VALUES
          (
            'static.v1', 'Static Web', 'static', NULL,
            '{"evidence": ["index.html"], "archive_required": true}'::jsonb,
            '{"entrypoint": "index.html", "health_path": "/"}'::jsonb,
            '{"memory_mb": 128, "cpus": 0.25, "pids": 32}'::jsonb
          ),
          (
            'python3.12.v1', 'Python 3.12 API', 'python', 'python:3.12-slim',
            '{"evidence_any": ["requirements.txt","pyproject.toml","app.py"]}'::jsonb,
            '{"port": 8080, "health_path": "/health", "default_entrypoint": "app.py"}'::jsonb,
            '{"memory_mb": 512, "cpus": 0.5, "pids": 128}'::jsonb
          ),
          (
            'node20.v1', 'Node.js 20 Web/API', 'node', 'node:20-alpine',
            '{"evidence": ["package.json"]}'::jsonb,
            '{"port": 8080, "health_path": "/health"}'::jsonb,
            '{"memory_mb": 512, "cpus": 0.5, "pids": 128}'::jsonb
          );

        ALTER TABLE digital_asset.deployments
          ADD COLUMN idempotency_key text,
          ADD COLUMN request_digest text
            CHECK (request_digest IS NULL OR request_digest ~ '^[a-f0-9]{64}$'),
          ADD COLUMN requested_credential_id uuid,
          ADD COLUMN runtime_profile_key text
            REFERENCES platform.runtime_profiles(profile_key),
          ADD COLUMN lease_owner text,
          ADD COLUMN lease_expires_at timestamptz,
          ADD COLUMN attempt_count integer NOT NULL DEFAULT 0
            CHECK (attempt_count >= 0),
          ADD COLUMN started_at timestamptz,
          ADD COLUMN completed_at timestamptz,
          ADD CONSTRAINT fk_deployments_requested_credential
            FOREIGN KEY (tenant_id, requested_credential_id)
            REFERENCES digital_asset.api_credentials(tenant_id, id);

        CREATE UNIQUE INDEX uq_deployments_workspace_idempotency
          ON digital_asset.deployments(tenant_id, workspace_id, idempotency_key)
          WHERE idempotency_key IS NOT NULL;
        CREATE INDEX idx_deployments_runtime_queue
          ON digital_asset.deployments(status, lease_expires_at, created_at)
          WHERE status IN ('queued','building','deploying');

        ALTER TABLE digital_asset.workspaces
          ADD COLUMN active_deployment_id uuid
            REFERENCES digital_asset.deployments(id) ON DELETE SET NULL;

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES (
          'digital_asset.deployment.runtime_verified_ready',
          'digital_asset.deployment',
          '部署只有在 Runtime 健康探測後才可成為 ready，永久入口只切換到已驗證版本',
          'external_verification',
          '{"ready_requires": {"status": "ready", "health": "healthy"}, "events": "append_only", "source_digest_required": true}'::jsonb
        ) ON CONFLICT (invariant_key) DO UPDATE SET
          description = EXCLUDED.description,
          enforcement = EXCLUDED.enforcement,
          machine_contract = EXCLUDED.machine_contract,
          active = true;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key = 'digital_asset.deployment.runtime_verified_ready';
        ALTER TABLE digital_asset.workspaces
          DROP COLUMN IF EXISTS active_deployment_id;
        DROP INDEX IF EXISTS digital_asset.idx_deployments_runtime_queue;
        DROP INDEX IF EXISTS digital_asset.uq_deployments_workspace_idempotency;
        ALTER TABLE digital_asset.deployments
          DROP CONSTRAINT IF EXISTS fk_deployments_requested_credential,
          DROP COLUMN IF EXISTS completed_at,
          DROP COLUMN IF EXISTS started_at,
          DROP COLUMN IF EXISTS attempt_count,
          DROP COLUMN IF EXISTS lease_expires_at,
          DROP COLUMN IF EXISTS lease_owner,
          DROP COLUMN IF EXISTS runtime_profile_key,
          DROP COLUMN IF EXISTS requested_credential_id,
          DROP COLUMN IF EXISTS request_digest,
          DROP COLUMN IF EXISTS idempotency_key;
        DROP TABLE IF EXISTS platform.runtime_profiles;
        """
    )
