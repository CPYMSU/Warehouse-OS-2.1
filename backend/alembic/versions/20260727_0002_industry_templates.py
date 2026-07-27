"""Add the versioned 13-industry tenant template catalogue.

Revision ID: 20260727_0002
Revises: 20260727_0001
Create Date: 2026-07-27
"""

from __future__ import annotations

import json

from sqlalchemy import text

from alembic import op
from app.templates.industry_blueprints import get_all_blueprints

revision = "20260727_0002"
down_revision = "20260727_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE iam.industry_templates (
          template_key text PRIMARY KEY CHECK (template_key ~ '^[a-z][a-z0-9_]{1,62}$'),
          name text NOT NULL CHECK (length(trim(name)) > 0),
          description text NOT NULL CHECK (length(trim(description)) > 0),
          schema_version smallint NOT NULL CHECK (schema_version > 0),
          revision text NOT NULL CHECK (length(trim(revision)) > 0),
          blueprint jsonb NOT NULL CHECK (jsonb_typeof(blueprint) = 'object'),
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE iam.organizational_units (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          template_key text NOT NULL REFERENCES iam.industry_templates(template_key) ON DELETE RESTRICT,
          unit_code text NOT NULL,
          name text NOT NULL CHECK (length(trim(name)) > 0),
          name_en text,
          description text NOT NULL DEFAULT '',
          unit_type text NOT NULL CHECK (unit_type IN ('company', 'department', 'team', 'project', 'other')),
          parent_unit_code text,
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, unit_code),
          UNIQUE (tenant_id, id)
        );
        CREATE INDEX idx_organizational_units_tenant_parent
          ON iam.organizational_units(tenant_id, parent_unit_code, unit_code);

        CREATE TABLE iam.position_profiles (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          template_key text NOT NULL REFERENCES iam.industry_templates(template_key) ON DELETE RESTRICT,
          position_code text NOT NULL,
          department_code text NOT NULL,
          name text NOT NULL CHECK (length(trim(name)) > 0),
          name_en text,
          role_name text NOT NULL CHECK (length(trim(role_name)) > 0),
          role_level smallint NOT NULL CHECK (role_level BETWEEN 1 AND 10),
          is_manager boolean NOT NULL DEFAULT false,
          permissions jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(permissions) = 'array'),
          database_access jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(database_access) = 'object'),
          navigation_defaults jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(navigation_defaults) = 'array'),
          public_entry jsonb,
          case_roles jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(case_roles) = 'array'),
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, position_code),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, department_code)
            REFERENCES iam.organizational_units(tenant_id, unit_code) ON DELETE RESTRICT
        );
        CREATE INDEX idx_position_profiles_tenant_department
          ON iam.position_profiles(tenant_id, department_code, role_level DESC);

        ALTER TABLE iam.tenants ADD COLUMN industry_template_key text;
        ALTER TABLE iam.memberships ADD COLUMN position_code text;

        CREATE TRIGGER trg_industry_templates_updated
          BEFORE UPDATE ON iam.industry_templates
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_organizational_units_updated
          BEFORE UPDATE ON iam.organizational_units
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_position_profiles_updated
          BEFORE UPDATE ON iam.position_profiles
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE iam.organizational_units ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.organizational_units FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.organizational_units
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE iam.position_profiles ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.position_profiles FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.position_profiles
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT SELECT ON iam.industry_templates TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE, DELETE ON iam.organizational_units, iam.position_profiles TO warehouse_os;
        """
    )

    insert_template = text(
        """
        INSERT INTO iam.industry_templates(
          template_key, name, description, schema_version, revision, blueprint
        ) VALUES (
          :template_key, :name, :description, :schema_version, :revision,
          CAST(:blueprint AS jsonb)
        )
        """
    )
    connection = op.get_bind()
    for template in get_all_blueprints().values():
        connection.execute(
            insert_template,
            {
                "template_key": template["key"],
                "name": template["name"],
                "description": template["description"],
                "schema_version": template["schema_version"],
                "revision": template["revision"],
                "blueprint": json.dumps(template, ensure_ascii=False),
            },
        )

    op.execute(
        """
        UPDATE iam.tenants
          SET industry_template_key = 'generic_warehouse'
          WHERE industry_template_key IS NULL;
        ALTER TABLE iam.tenants
          ALTER COLUMN industry_template_key SET NOT NULL,
          ALTER COLUMN industry_template_key SET DEFAULT 'generic_warehouse',
          ADD CONSTRAINT fk_iam_tenants_industry_template
            FOREIGN KEY (industry_template_key)
            REFERENCES iam.industry_templates(template_key) ON DELETE RESTRICT;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE iam.memberships DROP COLUMN IF EXISTS position_code;
        ALTER TABLE iam.tenants DROP COLUMN IF EXISTS industry_template_key;
        DROP TABLE IF EXISTS iam.position_profiles;
        DROP TABLE IF EXISTS iam.organizational_units;
        DROP TABLE IF EXISTS iam.industry_templates;
        """
    )
