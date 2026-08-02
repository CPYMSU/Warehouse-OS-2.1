"""Backfill employment and personnel files inside every tenant RLS context.

Revision ID: 20260802_0053
Revises: 20260802_0052
"""

from __future__ import annotations

from alembic import op

revision = "20260802_0053"
down_revision = "20260802_0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
          tenant_row record;
          member_row record;
          assigned_number bigint;
          next_available bigint;
          tenant_prefix text;
          personnel_file_id uuid;
        BEGIN
          FOR tenant_row IN SELECT id, slug FROM iam.tenants ORDER BY id LOOP
            PERFORM set_config('app.tenant_id', tenant_row.id::text, true);
            tenant_prefix := CASE
              WHEN regexp_replace(tenant_row.slug, '[^a-z0-9]', '', 'g') = '' THEN 'EMP'
              ELSE upper(left(regexp_replace(tenant_row.slug, '[^a-z0-9]', '', 'g'), 4))
            END;

            SELECT COALESCE(
              max(
                CASE WHEN employee_no ~ '-[0-9]+$'
                  THEN substring(employee_no FROM '([0-9]+)$')::bigint
                END
              ),
              0
            ) + 1
            INTO next_available
            FROM iam.employment_profiles;

            INSERT INTO iam.employment_sequences(tenant_id, next_number)
            VALUES (tenant_row.id, next_available)
            ON CONFLICT (tenant_id) DO UPDATE
              SET next_number = greatest(
                    iam.employment_sequences.next_number,
                    EXCLUDED.next_number
                  ),
                  updated_at = now();

            FOR member_row IN
              SELECT m.user_id, m.created_at
              FROM iam.memberships AS m
              LEFT JOIN iam.employment_profiles AS ep
                ON ep.tenant_id = m.tenant_id AND ep.user_id = m.user_id
              WHERE ep.user_id IS NULL
              ORDER BY m.created_at, m.user_id
            LOOP
              UPDATE iam.employment_sequences
              SET next_number = next_number + 1, updated_at = now()
              WHERE tenant_id = tenant_row.id
              RETURNING next_number - 1 INTO assigned_number;

              INSERT INTO iam.employment_profiles(
                tenant_id, user_id, employee_no, employment_type,
                employment_date, metadata
              ) VALUES (
                tenant_row.id, member_row.user_id,
                tenant_prefix || '-' || lpad(assigned_number::text, 5, '0'),
                'unspecified', member_row.created_at::date,
                jsonb_build_object(
                  'employment_date_source', 'membership_created_at',
                  'backfilled_at', now()
                )
              );
            END LOOP;

            FOR member_row IN
              SELECT ep.user_id, ep.employee_no, ep.employment_type,
                     ep.employment_date, u.display_name,
                     COALESCE(up.revision, 0) AS profile_revision,
                     COALESCE(up.profile->>'display_name', u.display_name)
                       AS profile_display_name
              FROM iam.employment_profiles AS ep
              JOIN iam.users AS u ON u.id = ep.user_id
              LEFT JOIN iam.user_profiles AS up ON up.user_id = ep.user_id
              LEFT JOIN records.personnel_files AS pf
                ON pf.tenant_id = ep.tenant_id AND pf.user_id = ep.user_id
              WHERE pf.id IS NULL
              ORDER BY ep.employee_no
            LOOP
              personnel_file_id := gen_random_uuid();
              INSERT INTO records.personnel_files(
                id, tenant_id, user_id, record_no, status, current_version,
                last_synced_profile_revision, last_synced_at
              ) VALUES (
                personnel_file_id, tenant_row.id, member_row.user_id,
                'HR-' || member_row.employee_no, 'active', 1,
                member_row.profile_revision, now()
              );

              INSERT INTO records.personnel_file_versions(
                tenant_id, personnel_file_id, version_no, profile_revision,
                snapshot, content_hash, created_by
              ) VALUES (
                tenant_row.id, personnel_file_id, 1,
                member_row.profile_revision,
                jsonb_build_object(
                  'schema', 'warehouse.personnel-file.v1',
                  'source', 'tenant_rls_backfill',
                  'display_name', member_row.display_name,
                  'profile', jsonb_build_object(
                    'display_name', member_row.profile_display_name
                  ),
                  'employment', jsonb_build_object(
                    'employee_no', member_row.employee_no,
                    'employment_type', member_row.employment_type,
                    'employment_date', member_row.employment_date
                  )
                ),
                'md5:' || md5(
                  member_row.user_id::text || '-' || member_row.profile_revision::text
                ),
                member_row.user_id
              );

              INSERT INTO compatibility.documents(
                id, tenant_id, namespace, document_key, status, payload,
                source, version, updated_by
              ) VALUES (
                personnel_file_id, tenant_row.id, 'record',
                'personnel:' || member_row.user_id::text, 'active',
                jsonb_build_object(
                  'id', personnel_file_id::text,
                  'record_no', 'HR-' || member_row.employee_no,
                  'type_id', 'personnel_record',
                  'type_key', 'personnel_record',
                  'category_key', 'personnel',
                  'category_name_snapshot', '人員檔案',
                  'title', member_row.display_name || ' · 人員檔案',
                  'description', '由個人中心與正式組織資料自動同步',
                  'status', 'active',
                  'confidentiality', 'restricted',
                  'subject_user_id', member_row.user_id::text,
                  'lock_version', 1,
                  'documents', '[]'::jsonb,
                  'events', jsonb_build_array(jsonb_build_object(
                    'event_type', 'personnel_file_provisioned',
                    'actor_name', 'Warehouse OS',
                    'created_at', now()
                  )),
                  'relations', '[]'::jsonb,
                  'created_at', now(),
                  'updated_at', now()
                ),
                'migration', 1, member_row.user_id
              )
              ON CONFLICT (tenant_id, namespace, document_key) DO NOTHING;
            END LOOP;

            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (
              tenant_row.id, NULL, 'records.personnel_backfill.completed',
              jsonb_build_object(
                'employment_profiles', (
                  SELECT count(*) FROM iam.employment_profiles
                ),
                'personnel_files', (
                  SELECT count(*) FROM records.personnel_files
                )
              )
            );
          END LOOP;
          PERFORM set_config('app.tenant_id', '', true);
        END;
        $$;
        """
    )


def downgrade() -> None:
    # The backfill populates durable records created by the preceding schema
    # migration.  Rolling that schema back removes them; this data migration
    # therefore has no independent destructive downgrade.
    pass
