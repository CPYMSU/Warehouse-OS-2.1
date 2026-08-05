"""Backfill the research capability contract through tenant-scoped RLS.

Revision ID: 20260731_0028
Revises: 20260731_0027
Create Date: 2026-07-31
"""

from __future__ import annotations

import json

from sqlalchemy import text

from alembic import op
from app.templates.industry_blueprints import (
    blueprint_nav_ceilings,
    blueprint_nav_defaults,
    blueprint_permission_ceilings,
    get_all_blueprints,
)

revision = "20260731_0028"
down_revision = "20260731_0027"
branch_labels = None
depends_on = None

RESEARCH_PERMISSION_KEYS = frozenset(
    {"research.read", "research.write", "research.review"}
)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def upgrade() -> None:
    bind = op.get_bind()
    blueprints = get_all_blueprints()
    template_contracts: list[dict[str, object]] = []
    position_contracts: list[dict[str, object]] = []
    department_contracts: list[dict[str, object]] = []
    for blueprint in blueprints.values():
        template_key = str(blueprint["key"])
        template_contracts.append(
            {
                "template_key": template_key,
                "name": blueprint["name"],
                "description": blueprint["description"],
                "schema_version": blueprint["schema_version"],
                "revision": blueprint["revision"],
                "blueprint": blueprint,
            }
        )
        navigation_defaults = blueprint_nav_defaults(blueprint)
        for position in blueprint.get("positions") or ():
            position_code = str(position["code"])
            position_contracts.append(
                {
                    "template_key": template_key,
                    "position_code": position_code,
                    "permissions": sorted(
                        RESEARCH_PERMISSION_KEYS.intersection(
                            position.get("permissions") or ()
                        )
                    ),
                    "research_navigation": (
                        "research" in navigation_defaults.get(position_code, ())
                    ),
                }
            )
        permission_ceilings = blueprint_permission_ceilings(blueprint)
        navigation_ceilings = blueprint_nav_ceilings(blueprint)
        for department in blueprint.get("departments") or ():
            department_code = str(department["code"])
            full_permissions = permission_ceilings.get(department_code) or []
            full_navigation = navigation_ceilings.get(department_code) or []
            department_contracts.append(
                {
                    "template_key": template_key,
                    "department_code": department_code,
                    "full_permissions": full_permissions,
                    "research_permissions": sorted(
                        RESEARCH_PERMISSION_KEYS.intersection(full_permissions)
                    ),
                    "full_navigation": full_navigation,
                    "research_navigation": "research" in full_navigation,
                }
            )

    # JSON recordsets keep the migration data frozen for this transaction while
    # avoiding thousands of client/server round trips.
    bind.execute(
        text(
            """
            CREATE TEMP TABLE research_template_contracts(
              template_key text PRIMARY KEY,
              name text NOT NULL,
              description text NOT NULL,
              schema_version smallint NOT NULL,
              revision text NOT NULL,
              blueprint jsonb NOT NULL
            ) ON COMMIT DROP
            """
        )
    )
    bind.execute(
        text(
            """
            INSERT INTO research_template_contracts
            SELECT *
            FROM jsonb_to_recordset(CAST(:contracts AS jsonb)) AS contract(
              template_key text,
              name text,
              description text,
              schema_version smallint,
              revision text,
              blueprint jsonb
            )
            """
        ),
        {"contracts": _json(template_contracts)},
    )
    bind.execute(
        text(
            """
            UPDATE iam.industry_templates AS target
            SET name = contract.name,
                description = contract.description,
                schema_version = contract.schema_version,
                revision = contract.revision,
                blueprint = contract.blueprint
            FROM research_template_contracts AS contract
            WHERE target.template_key = contract.template_key
            """
        )
    )

    bind.execute(
        text(
            """
            CREATE TEMP TABLE research_position_contracts(
              template_key text NOT NULL,
              position_code text NOT NULL,
              permissions jsonb NOT NULL,
              research_navigation boolean NOT NULL,
              PRIMARY KEY (template_key, position_code)
            ) ON COMMIT DROP
            """
        )
    )
    bind.execute(
        text(
            """
            INSERT INTO research_position_contracts
            SELECT *
            FROM jsonb_to_recordset(CAST(:contracts AS jsonb)) AS contract(
              template_key text,
              position_code text,
              permissions jsonb,
              research_navigation boolean
            )
            """
        ),
        {"contracts": _json(position_contracts)},
    )
    bind.execute(
        text(
            """
            CREATE TEMP TABLE research_department_contracts(
              template_key text NOT NULL,
              department_code text NOT NULL,
              full_permissions jsonb NOT NULL,
              research_permissions jsonb NOT NULL,
              full_navigation jsonb NOT NULL,
              research_navigation boolean NOT NULL,
              PRIMARY KEY (template_key, department_code)
            ) ON COMMIT DROP
            """
        )
    )
    bind.execute(
        text(
            """
            INSERT INTO research_department_contracts
            SELECT *
            FROM jsonb_to_recordset(CAST(:contracts AS jsonb)) AS contract(
              template_key text,
              department_code text,
              full_permissions jsonb,
              research_permissions jsonb,
              full_navigation jsonb,
              research_navigation boolean
            )
            """
        ),
        {"contracts": _json(department_contracts)},
    )

    # RLS remains forced throughout. The server-side loop switches the
    # transaction-local tenant before each set-based tenant mutation.
    op.execute(
        """
        DO $migration$
        DECLARE
          tenant record;
        BEGIN
          FOR tenant IN
            SELECT id, industry_template_key
            FROM iam.tenants
            WHERE industry_template_key IN (
              SELECT template_key FROM research_template_contracts
            )
            ORDER BY created_at, id
          LOOP
            PERFORM set_config('app.tenant_id', tenant.id::text, true);

            UPDATE iam.position_profiles AS profile
            SET permissions = COALESCE((
                  SELECT jsonb_agg(value ORDER BY value)
                  FROM (
                    SELECT DISTINCT value
                    FROM jsonb_array_elements_text(
                      profile.permissions || contract.permissions
                    ) AS merged(value)
                  ) AS distinct_permissions
                ), '[]'::jsonb),
                navigation_defaults = CASE
                  WHEN contract.research_navigation
                       AND NOT profile.navigation_defaults @> '["research"]'::jsonb
                    THEN profile.navigation_defaults || '["research"]'::jsonb
                  ELSE profile.navigation_defaults
                END
            FROM research_position_contracts AS contract
            WHERE profile.tenant_id = tenant.id
              AND contract.template_key = tenant.industry_template_key
              AND contract.position_code = profile.position_code
              AND (
                NOT profile.permissions @> contract.permissions
                OR (
                  contract.research_navigation
                  AND NOT profile.navigation_defaults @> '["research"]'::jsonb
                )
              );

            INSERT INTO iam.department_access_policies(
              tenant_id, org_unit_id, permission_ceiling_enabled,
              permission_ceiling, navigation_ceiling_enabled,
              navigation_ceiling
            )
            SELECT tenant.id, unit.id, true, contract.full_permissions,
                   true, contract.full_navigation
            FROM iam.organizational_units AS unit
            JOIN research_department_contracts AS contract
              ON contract.template_key = tenant.industry_template_key
             AND contract.department_code = unit.unit_code
            WHERE unit.tenant_id = tenant.id
            ON CONFLICT (tenant_id, org_unit_id) DO NOTHING;

            UPDATE iam.department_access_policies AS policy
            SET permission_ceiling = COALESCE((
                  SELECT jsonb_agg(value ORDER BY value)
                  FROM (
                    SELECT DISTINCT value
                    FROM jsonb_array_elements_text(
                      policy.permission_ceiling || contract.research_permissions
                    ) AS merged(value)
                  ) AS distinct_permissions
                ), '[]'::jsonb),
                navigation_ceiling = CASE
                  WHEN contract.research_navigation
                       AND NOT policy.navigation_ceiling @> '["research"]'::jsonb
                    THEN policy.navigation_ceiling || '["research"]'::jsonb
                  ELSE policy.navigation_ceiling
                END
            FROM iam.organizational_units AS unit
            JOIN research_department_contracts AS contract
              ON contract.template_key = tenant.industry_template_key
             AND contract.department_code = unit.unit_code
            WHERE policy.tenant_id = tenant.id
              AND unit.tenant_id = policy.tenant_id
              AND unit.id = policy.org_unit_id
              AND (
                NOT policy.permission_ceiling @> contract.research_permissions
                OR (
                  contract.research_navigation
                  AND NOT policy.navigation_ceiling @> '["research"]'::jsonb
                )
              );

            INSERT INTO audit.events(tenant_id, event_type, payload)
            SELECT tenant.id,
                   'research.permission_contract_backfilled',
                   jsonb_build_object(
                     'template_key', tenant.industry_template_key,
                     'revision', contract.revision,
                     'permissions', '["research.read","research.write","research.review"]'::jsonb,
                     'source', 'tenant_scoped_capability_contract'
                   )
            FROM research_template_contracts AS contract
            WHERE contract.template_key = tenant.industry_template_key;
          END LOOP;
        END
        $migration$;
        """
    )


def downgrade() -> None:
    # These keys may have been intentionally delegated after the upgrade.
    # Removing them automatically would destroy valid tenant policy.
    pass
