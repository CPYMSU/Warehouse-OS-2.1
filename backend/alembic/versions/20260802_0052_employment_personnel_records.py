"""Add employment identity projection and versioned personnel records.

Revision ID: 20260802_0052
Revises: 20260802_0051
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0052"
down_revision = "20260802_0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS records;

        CREATE TABLE iam.employment_sequences (
          tenant_id uuid PRIMARY KEY REFERENCES iam.tenants(id) ON DELETE CASCADE,
          next_number bigint NOT NULL DEFAULT 1 CHECK (next_number > 0),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE iam.employment_profiles (
          tenant_id uuid NOT NULL,
          user_id uuid NOT NULL,
          employee_no text NOT NULL
            CHECK (employee_no ~ '^[A-Z0-9][A-Z0-9-]{2,31}$'),
          employment_type text NOT NULL DEFAULT 'unspecified'
            CHECK (employment_type IN (
              'unspecified', 'employee', 'contractor', 'visiting',
              'intern', 'affiliate', 'other'
            )),
          employment_date date,
          manager_user_id uuid,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            CHECK (jsonb_typeof(metadata) = 'object'),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, user_id),
          UNIQUE (tenant_id, employee_no),
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, manager_user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE RESTRICT,
          CHECK (manager_user_id IS NULL OR manager_user_id <> user_id)
        );
        CREATE INDEX idx_employment_profiles_manager
          ON iam.employment_profiles(tenant_id, manager_user_id)
          WHERE manager_user_id IS NOT NULL;

        CREATE TABLE records.personnel_files (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          user_id uuid NOT NULL,
          record_no text NOT NULL CHECK (length(trim(record_no)) BETWEEN 3 AND 80),
          status text NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'pending_review', 'archived')),
          current_version integer NOT NULL DEFAULT 0 CHECK (current_version >= 0),
          last_synced_profile_revision integer NOT NULL DEFAULT 0
            CHECK (last_synced_profile_revision >= 0),
          pending_review_count integer NOT NULL DEFAULT 0
            CHECK (pending_review_count >= 0),
          last_synced_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, user_id),
          UNIQUE (tenant_id, record_no),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, user_id)
            REFERENCES iam.memberships(tenant_id, user_id) ON DELETE CASCADE
        );

        CREATE TABLE records.personnel_file_versions (
          tenant_id uuid NOT NULL,
          personnel_file_id uuid NOT NULL,
          version_no integer NOT NULL CHECK (version_no > 0),
          profile_revision integer NOT NULL CHECK (profile_revision >= 0),
          snapshot jsonb NOT NULL CHECK (jsonb_typeof(snapshot) = 'object'),
          content_hash text NOT NULL,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id, personnel_file_id, version_no),
          UNIQUE (tenant_id, personnel_file_id, profile_revision),
          FOREIGN KEY (tenant_id, personnel_file_id)
            REFERENCES records.personnel_files(tenant_id, id) ON DELETE CASCADE
        );
        CREATE INDEX idx_personnel_file_versions_recent
          ON records.personnel_file_versions(tenant_id, personnel_file_id, created_at DESC);

        WITH ranked AS (
          SELECT m.tenant_id, m.user_id, m.created_at,
                 row_number() OVER (
                   PARTITION BY m.tenant_id ORDER BY m.created_at, m.user_id
                 ) AS employee_number,
                 upper(left(regexp_replace(t.slug, '[^a-z0-9]', '', 'g'), 4)) AS prefix
          FROM iam.memberships AS m
          JOIN iam.tenants AS t ON t.id = m.tenant_id
        )
        INSERT INTO iam.employment_profiles(
          tenant_id, user_id, employee_no, employment_type, employment_date, metadata
        )
        SELECT tenant_id, user_id,
               CASE WHEN prefix = '' THEN 'EMP' ELSE prefix END || '-' ||
                 lpad(employee_number::text, 5, '0'),
               'unspecified', created_at::date,
               jsonb_build_object('employment_date_source', 'membership_created_at')
        FROM ranked;

        INSERT INTO iam.employment_sequences(tenant_id, next_number)
        SELECT tenant_id, count(*) + 1 FROM iam.memberships GROUP BY tenant_id;

        INSERT INTO records.personnel_files(
          id, tenant_id, user_id, record_no, status, current_version,
          last_synced_profile_revision, last_synced_at
        )
        SELECT gen_random_uuid(), ep.tenant_id, ep.user_id,
               'HR-' || ep.employee_no, 'active', 1,
               COALESCE(up.revision, 0), now()
        FROM iam.employment_profiles AS ep
        LEFT JOIN iam.user_profiles AS up ON up.user_id = ep.user_id;

        INSERT INTO records.personnel_file_versions(
          tenant_id, personnel_file_id, version_no, profile_revision,
          snapshot, content_hash, created_by
        )
        SELECT pf.tenant_id, pf.id, 1, pf.last_synced_profile_revision,
               jsonb_build_object(
                 'schema', 'warehouse.personnel-file.v1',
                 'source', 'membership_migration',
                 'display_name', u.display_name,
                 'profile', jsonb_build_object(
                   'display_name', COALESCE(up.profile->>'display_name', u.display_name)
                 ),
                 'employment', jsonb_build_object(
                   'employee_no', ep.employee_no,
                   'employment_type', ep.employment_type,
                   'employment_date', ep.employment_date
                 )
               ),
               'md5:' || md5(
                 jsonb_build_object(
                   'user_id', pf.user_id,
                   'profile_revision', pf.last_synced_profile_revision
                 )::text
               ),
               pf.user_id
        FROM records.personnel_files AS pf
        JOIN iam.users AS u ON u.id = pf.user_id
        JOIN iam.employment_profiles AS ep
          ON ep.tenant_id = pf.tenant_id AND ep.user_id = pf.user_id
        LEFT JOIN iam.user_profiles AS up ON up.user_id = pf.user_id;

        INSERT INTO compatibility.documents(
          id, tenant_id, namespace, document_key, status, payload,
          source, version, updated_by
        )
        SELECT pf.id, pf.tenant_id, 'record', 'personnel:' || pf.user_id::text,
               'active',
               jsonb_build_object(
                 'id', pf.id::text,
                 'record_no', pf.record_no,
                 'type_id', 'personnel_record',
                 'type_key', 'personnel_record',
                 'category_key', 'personnel',
                 'category_name_snapshot', '人員檔案',
                 'title', u.display_name || ' · 人員檔案',
                 'description', '由個人中心與正式組織資料自動同步',
                 'status', pf.status,
                 'confidentiality', 'restricted',
                 'subject_user_id', pf.user_id::text,
                 'lock_version', pf.current_version,
                 'documents', '[]'::jsonb,
                 'events', jsonb_build_array(jsonb_build_object(
                   'event_type', 'personnel_file_provisioned',
                   'actor_name', 'Warehouse OS',
                   'created_at', pf.created_at
                 )),
                 'relations', '[]'::jsonb,
                 'created_at', pf.created_at,
                 'updated_at', pf.updated_at
               ),
               'migration', 1, pf.user_id
        FROM records.personnel_files AS pf
        JOIN iam.users AS u ON u.id = pf.user_id
        ON CONFLICT (tenant_id, namespace, document_key) DO NOTHING;

        CREATE TRIGGER trg_employment_profiles_updated
          BEFORE UPDATE ON iam.employment_profiles
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_personnel_files_updated
          BEFORE UPDATE ON records.personnel_files
          FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        ALTER TABLE iam.employment_sequences ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.employment_sequences FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.employment_sequences
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE iam.employment_profiles ENABLE ROW LEVEL SECURITY;
        ALTER TABLE iam.employment_profiles FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON iam.employment_profiles
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE records.personnel_files ENABLE ROW LEVEL SECURITY;
        ALTER TABLE records.personnel_files FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON records.personnel_files
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());
        ALTER TABLE records.personnel_file_versions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE records.personnel_file_versions FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON records.personnel_file_versions
          USING (tenant_id = app.current_tenant_id())
          WITH CHECK (tenant_id = app.current_tenant_id());

        GRANT USAGE ON SCHEMA records TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON iam.employment_sequences,
          iam.employment_profiles TO warehouse_os;
        GRANT SELECT, INSERT, UPDATE ON records.personnel_files TO warehouse_os;
        GRANT SELECT, INSERT ON records.personnel_file_versions TO warehouse_os;

        CREATE OR REPLACE FUNCTION app.provision_employment_identity()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
        DECLARE
          assigned_number bigint;
          tenant_slug text;
          employee_number text;
          personnel_file_id uuid;
        BEGIN
          PERFORM set_config('app.tenant_id', NEW.tenant_id::text, true);
          SELECT slug INTO tenant_slug FROM iam.tenants WHERE id = NEW.tenant_id;
          INSERT INTO iam.employment_sequences(tenant_id, next_number)
          VALUES (NEW.tenant_id, 2)
          ON CONFLICT (tenant_id) DO UPDATE
            SET next_number = iam.employment_sequences.next_number + 1,
                updated_at = now()
          RETURNING next_number - 1 INTO assigned_number;
          employee_number := CASE
            WHEN regexp_replace(tenant_slug, '[^a-z0-9]', '', 'g') = '' THEN 'EMP'
            ELSE upper(left(regexp_replace(tenant_slug, '[^a-z0-9]', '', 'g'), 4))
          END || '-' || lpad(assigned_number::text, 5, '0');

          INSERT INTO iam.employment_profiles(
            tenant_id, user_id, employee_no, employment_type,
            employment_date, metadata
          ) VALUES (
            NEW.tenant_id, NEW.user_id, employee_number, 'unspecified',
            NEW.created_at::date,
            jsonb_build_object('employment_date_source', 'membership_created_at')
          );

          personnel_file_id := gen_random_uuid();
          INSERT INTO records.personnel_files(
            id, tenant_id, user_id, record_no, status, current_version,
            last_synced_profile_revision, last_synced_at
          ) VALUES (
            personnel_file_id, NEW.tenant_id, NEW.user_id,
            'HR-' || employee_number, 'active', 1, 0, now()
          );
          INSERT INTO records.personnel_file_versions(
            tenant_id, personnel_file_id, version_no, profile_revision,
            snapshot, content_hash, created_by
          ) VALUES (
            NEW.tenant_id, personnel_file_id, 1, 0,
            jsonb_build_object(
              'schema', 'warehouse.personnel-file.v1',
              'source', 'membership_created',
              'employment', jsonb_build_object('employee_no', employee_number)
            ),
            'md5:' || md5(NEW.user_id::text || '-0'), NEW.user_id
          );
          INSERT INTO compatibility.documents(
            id, tenant_id, namespace, document_key, status, payload,
            source, version, updated_by
          ) VALUES (
            personnel_file_id, NEW.tenant_id, 'record',
            'personnel:' || NEW.user_id::text, 'active',
            jsonb_build_object(
              'id', personnel_file_id::text,
              'record_no', 'HR-' || employee_number,
              'type_id', 'personnel_record',
              'type_key', 'personnel_record',
              'category_key', 'personnel',
              'category_name_snapshot', '人員檔案',
              'title', '人員檔案',
              'status', 'active',
              'confidentiality', 'restricted',
              'subject_user_id', NEW.user_id::text,
              'lock_version', 1,
              'documents', '[]'::jsonb,
              'events', '[]'::jsonb,
              'relations', '[]'::jsonb,
              'created_at', now(),
              'updated_at', now()
            ),
            'native', 1, NEW.user_id
          );
          RETURN NEW;
        END;
        $$;
        REVOKE ALL ON FUNCTION app.provision_employment_identity() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION app.provision_employment_identity() TO warehouse_os;
        CREATE TRIGGER trg_membership_employment_identity
          AFTER INSERT ON iam.memberships
          FOR EACH ROW EXECUTE FUNCTION app.provision_employment_identity();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_membership_employment_identity ON iam.memberships;
        DROP FUNCTION IF EXISTS app.provision_employment_identity();
        DROP TABLE IF EXISTS records.personnel_file_versions;
        DROP TABLE IF EXISTS records.personnel_files;
        DROP SCHEMA IF EXISTS records;
        DROP TABLE IF EXISTS iam.employment_profiles;
        DROP TABLE IF EXISTS iam.employment_sequences;
        """
    )
