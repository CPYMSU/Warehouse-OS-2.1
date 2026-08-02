"""Reserve custom hostnames globally before DNS/TLS activation.

Revision ID: 20260803_0062
Revises: 20260803_0061
"""

from __future__ import annotations

from alembic import op

revision = "20260803_0062"
down_revision = "20260803_0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        CREATE TABLE digital_asset.hosting_domain_claims (
          hostname text PRIMARY KEY
            CHECK (hostname=lower(hostname) AND hostname ~ '^[a-z0-9.-]+$'),
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          workspace_id uuid NOT NULL,
          claimed_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT hosting_domain_claims_workspace_fk
            FOREIGN KEY (tenant_id,workspace_id)
            REFERENCES digital_asset.workspaces(tenant_id,id) ON DELETE CASCADE
        );
        CREATE INDEX ix_hosting_domain_claims_workspace
          ON digital_asset.hosting_domain_claims(tenant_id,workspace_id);
        CREATE TRIGGER trg_hosting_domain_claims_updated
          BEFORE UPDATE ON digital_asset.hosting_domain_claims
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        GRANT SELECT,INSERT,UPDATE,DELETE
          ON digital_asset.hosting_domain_claims TO warehouse_os;
        ALTER TABLE digital_asset.hosting_domain_claims ENABLE ROW LEVEL SECURITY;
        ALTER TABLE digital_asset.hosting_domain_claims FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON digital_asset.hosting_domain_claims
          USING (tenant_id=app.current_tenant_id())
          WITH CHECK (tenant_id=app.current_tenant_id());

        INSERT INTO digital_asset.hosting_domain_claims(hostname,tenant_id,workspace_id)
        SELECT DISTINCT ON (resource_key)
               lower(resource_key),tenant_id,workspace_id
        FROM digital_asset.hosting_resources
        WHERE resource_kind='domain'
          AND resource_key ~ '^[A-Za-z0-9.-]+$'
        ORDER BY resource_key,created_at,id
        ON CONFLICT (hostname) DO NOTHING;

        UPDATE digital_asset.hosting_resources AS resource
        SET status='blocked',
            last_error=jsonb_build_object(
              'reason','hostname_claimed_by_another_workspace',
              'stage','domain_claim_reconciliation',
              'retryable',false
            )
        FROM digital_asset.hosting_domain_claims AS claim
        WHERE resource.resource_kind='domain'
          AND lower(resource.resource_key)=claim.hostname
          AND resource.workspace_id<>claim.workspace_id;

        INSERT INTO app.resource_invariants(
          invariant_key,resource_key,description,enforcement,machine_contract
        ) VALUES (
          'digital_asset.hosting_resource.domain_global_claim',
          'digital_asset.hosting_resource',
          '自訂 hostname 在全平台只能由一個工作區持有；平台主域與其子域不可由工作區 Key 佔用',
          'database',
          '{"hostname_primary_key":true,"tenant_rls":true,"platform_origin_reserved":true}'::jsonb
        ) ON CONFLICT (invariant_key) DO UPDATE SET
          description=EXCLUDED.description,enforcement=EXCLUDED.enforcement,
          machine_contract=EXCLUDED.machine_contract,active=true;

        UPDATE platform.hosting_fabric_drivers
        SET desired_schema='{"fields":{"url":"string","ref":"string","credential_secret":"string","component":"string","auto_sync":"boolean","sync_interval_seconds":"integer"}}'::jsonb,
            capability_contract='{"protocols":["https"],"credentials":"secret_reference","shallow":true,"automatic_sync":true,"minimum_interval_seconds":60}'::jsonb,
            revision=revision+1,updated_at=now()
        WHERE driver_key='git.repository.v1';

        UPDATE platform.hosting_fabric_drivers
        SET capability_contract=capability_contract ||
              '{"compose_route_autoscaling":true,"load_balancing":"stable_request_hash"}'::jsonb,
            revision=revision+1,updated_at=now()
        WHERE driver_key='runtime.scaling.v1';
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key='digital_asset.hosting_resource.domain_global_claim';
        DROP TABLE IF EXISTS digital_asset.hosting_domain_claims;
        """
    )
