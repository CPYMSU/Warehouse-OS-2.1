"""Add verified Swiss identity titles and position title metadata.

Revision ID: 20260802_0050
Revises: 20260802_0049
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0050"
down_revision = "20260802_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.title_definitions (
          code text PRIMARY KEY CHECK (code ~ '^[a-z][a-z0-9_]{1,63}$'),
          category text NOT NULL CHECK (category IN (
            'academic_degree', 'academic_appointment',
            'organizational_office', 'professional', 'honorary'
          )),
          label_zh_hant text NOT NULL CHECK (length(trim(label_zh_hant)) > 0),
          label_zh_hans text NOT NULL CHECK (length(trim(label_zh_hans)) > 0),
          label_en text NOT NULL CHECK (length(trim(label_en)) > 0),
          abbreviation text NOT NULL DEFAULT '',
          priority integer NOT NULL CHECK (priority BETWEEN 1 AND 999),
          name_prefix boolean NOT NULL DEFAULT false,
          claimable boolean NOT NULL DEFAULT false,
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        INSERT INTO iam.title_definitions(
          code, category, label_zh_hant, label_zh_hans, label_en,
          abbreviation, priority, name_prefix, claimable
        ) VALUES
          ('professor', 'academic_appointment', '教授', '教授', 'Professor', 'Prof.', 10, true, false),
          ('associate_professor', 'academic_appointment', '副教授', '副教授', 'Associate Professor', 'Assoc. Prof.', 11, true, false),
          ('assistant_professor', 'academic_appointment', '助理教授', '助理教授', 'Assistant Professor', 'Asst. Prof.', 12, true, false),
          ('doctor', 'academic_degree', '博士', '博士', 'Doctor', 'Dr.', 20, true, true),
          ('chief_accountant', 'professional', '首席會計師', '首席会计师', 'Chief Accountant', 'Chief Accountant', 35, false, true),
          ('cpa', 'professional', '註冊會計師', '注册会计师', 'Certified Public Accountant', 'CPA', 40, false, true),
          ('ceo', 'organizational_office', '首席執行官', '首席执行官', 'Chief Executive Officer', 'CEO', 50, false, false);

        ALTER TABLE iam.position_profiles
          ADD COLUMN title_code text REFERENCES iam.title_definitions(code) ON DELETE SET NULL;

        UPDATE iam.position_profiles
        SET title_code = CASE
          WHEN lower(position_code) LIKE '%assistant_professor%'
            OR name IN ('助理教授') THEN 'assistant_professor'
          WHEN lower(position_code) LIKE '%associate_professor%'
            OR name IN ('副教授') THEN 'associate_professor'
          WHEN lower(position_code) ~ '(^|_)professor($|_)'
            OR name IN ('教授') THEN 'professor'
          WHEN lower(position_code) IN ('ceo', 'chief_executive_officer')
            OR name IN ('首席執行官', '首席执行官', '執行長', '执行长') THEN 'ceo'
          WHEN lower(position_code) IN ('chief_accountant')
            OR name IN ('首席會計師', '首席会计师') THEN 'chief_accountant'
          ELSE title_code
        END;

        CREATE TABLE iam.person_title_claims (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          user_id uuid NOT NULL,
          title_code text NOT NULL REFERENCES iam.title_definitions(code) ON DELETE RESTRICT,
          source_kind text NOT NULL CHECK (source_kind IN (
            'verified_record', 'professional_registry', 'owner_attestation', 'legacy_verified'
          )),
          source_ref text NOT NULL DEFAULT '',
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'historical', 'revoked')),
          verified_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          valid_from timestamptz,
          valid_until timestamptz,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(metadata) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE,
          UNIQUE (tenant_id, user_id, title_code, source_kind, source_ref),
          CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from)
        );
        CREATE INDEX idx_person_title_claims_active
          ON iam.person_title_claims(tenant_id, user_id, status, title_code);

        CREATE TRIGGER trg_title_definitions_updated
          BEFORE UPDATE ON iam.title_definitions
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_person_title_claims_updated
          BEFORE UPDATE ON iam.person_title_claims
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE iam.person_title_claims ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.person_title_claims FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.person_title_claims
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT SELECT ON iam.title_definitions TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON iam.person_title_claims TO warehouse_os;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS iam.person_title_claims;
        ALTER TABLE iam.position_profiles DROP COLUMN IF EXISTS title_code;
        DROP TABLE IF EXISTS iam.title_definitions;
        """
    )
