"""Register canonical IAM members, roles, and semantic aliases.

Revision ID: 20260805_0075
Revises: 20260805_0074
"""

from __future__ import annotations

from alembic import op

revision = "20260805_0075"
down_revision = "20260805_0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE app.resource_types
          ADD COLUMN aliases jsonb NOT NULL DEFAULT '[]'::jsonb;
        ALTER TABLE app.resource_types
          ADD CONSTRAINT resource_types_aliases_array
          CHECK (jsonb_typeof(aliases) = 'array');
        CREATE INDEX idx_resource_types_aliases
          ON app.resource_types USING gin (aliases jsonb_path_ops);

        CREATE VIEW iam.member_directory
        WITH (security_invoker=true) AS
        SELECT
          users.id,
          membership.tenant_id,
          users.username,
          users.display_name,
          users.active AS user_active,
          membership.active AS membership_active,
          membership.position_code,
          position.id AS position_id,
          position.name AS position_name,
          position.role_name AS position_role_name,
          position.department_code,
          unit.id AS department_id,
          unit.name AS department_name,
          membership.role_level,
          membership.topology_level,
          membership.topology_title,
          GREATEST(
            users.updated_at,
            membership.updated_at,
            COALESCE(position.updated_at,membership.updated_at),
            COALESCE(unit.updated_at,membership.updated_at)
          ) AS updated_at
        FROM iam.memberships AS membership
        JOIN iam.users AS users ON users.id=membership.user_id
        LEFT JOIN iam.position_profiles AS position
          ON position.tenant_id=membership.tenant_id
         AND position.position_code=membership.position_code
        LEFT JOIN iam.organizational_units AS unit
          ON unit.tenant_id=membership.tenant_id
         AND unit.unit_code=position.department_code;

        CREATE VIEW iam.role_directory
        WITH (security_invoker=true) AS
        SELECT
          role.id,
          role.tenant_id,
          role.role_key,
          role.name,
          role.level,
          role.active,
          COALESCE(
            array_agg(permission.permission_key ORDER BY permission.permission_key)
              FILTER (WHERE permission.permission_key IS NOT NULL),
            '{}'::text[]
          ) AS permissions,
          role.created_at,
          role.updated_at
        FROM iam.roles AS role
        LEFT JOIN iam.role_permissions AS permission
          ON permission.tenant_id=role.tenant_id AND permission.role_id=role.id
        GROUP BY role.id;

        GRANT SELECT ON iam.member_directory,iam.role_directory TO warehouse_os;

        UPDATE app.resource_types SET aliases='["org:department","org:unit"]'::jsonb
        WHERE resource_key='iam.organizational_unit';
        UPDATE app.resource_types SET aliases='["org:position","org:job"]'::jsonb
        WHERE resource_key='iam.position_profile';

        INSERT INTO app.resource_types(
          resource_key,label,description,storage_schema,storage_table,
          version_column,version_strategy,identity_fields,allowed_effects,aliases
        ) VALUES
          (
            'iam.member','成員帳號',
            '真實全局登入身份在當前公司的成員、部門與主崗位投影；寫入必須使用原子成員適配器',
            'iam','member_directory','updated_at','timestamp',
            '["id","username","display_name"]','["read","query"]',
            '["org:member","org:user","iam:user"]'
          ),
          (
            'iam.role','訪問角色',
            '真實公司 RBAC 訪問角色及權限集合；與組織崗位分離',
            'iam','role_directory','updated_at','timestamp',
            '["id","role_key","name"]','["read","query"]',
            '["auth:role","rbac:role"]'
          )
        ON CONFLICT (resource_key) DO UPDATE SET
          label=EXCLUDED.label,
          description=EXCLUDED.description,
          storage_schema=EXCLUDED.storage_schema,
          storage_table=EXCLUDED.storage_table,
          version_column=EXCLUDED.version_column,
          version_strategy=EXCLUDED.version_strategy,
          identity_fields=EXCLUDED.identity_fields,
          allowed_effects=EXCLUDED.allowed_effects,
          aliases=EXCLUDED.aliases,
          active=true;

        INSERT INTO app.resource_fields(
          resource_key,field_key,label,semantic_description,data_type,
          nullable,editable_mode,sensitivity,storage_column,json_path,
          constraints,display_order
        ) VALUES
          ('iam.member','id','成員 UUID','全局登入身份 UUID','uuid',false,'immutable','normal','id','[]','{}',1),
          ('iam.member','username','登入帳號','全局唯一登入帳號','string',false,'immutable','personal','username','[]','{}',10),
          ('iam.member','display_name','姓名','成員顯示名稱','string',false,'adapter_only','personal','display_name','[]','{}',20),
          ('iam.member','user_active','登入啟用','全局登入身份是否啟用','boolean',false,'adapter_only','normal','user_active','[]','{}',30),
          ('iam.member','membership_active','公司成員啟用','當前公司成員關係是否啟用','boolean',false,'adapter_only','normal','membership_active','[]','{}',40),
          ('iam.member','position_code','主崗位代碼','當前公司主崗位穩定代碼','string',true,'adapter_only','normal','position_code','[]','{}',50),
          ('iam.member','position_id','主崗位 UUID','主崗位真實 UUID','uuid',true,'derived','normal','position_id','[]','{}',51),
          ('iam.member','position_name','主崗位','主崗位顯示名稱','string',true,'derived','normal','position_name','[]','{}',52),
          ('iam.member','position_role_name','崗位角色語義','崗位承擔的業務角色，不等同 RBAC 訪問角色','string',true,'derived','normal','position_role_name','[]','{}',53),
          ('iam.member','department_code','部門代碼','主崗位所屬部門穩定代碼','string',true,'derived','normal','department_code','[]','{}',60),
          ('iam.member','department_id','部門 UUID','主崗位所屬部門真實 UUID','uuid',true,'derived','normal','department_id','[]','{}',61),
          ('iam.member','department_name','部門','主崗位所屬部門名稱','string',true,'derived','normal','department_name','[]','{}',62),
          ('iam.member','role_level','權限級別','成員有效級別','integer',false,'derived','normal','role_level','[]','{"minimum":"1","maximum":"10"}',70),
          ('iam.member','topology_level','拓撲級別','組織拓撲級別','integer',false,'derived','normal','topology_level','[]','{"minimum":"1","maximum":"10"}',80),
          ('iam.member','topology_title','拓撲稱謂','組織拓撲顯示稱謂','string',true,'derived','normal','topology_title','[]','{}',90),
          ('iam.member','updated_at','更新時間','身份、成員、崗位或部門的最新變動時間','datetime',false,'derived','normal','updated_at','[]','{}',100),

          ('iam.role','id','角色 UUID','公司訪問角色 UUID','uuid',false,'immutable','normal','id','[]','{}',1),
          ('iam.role','role_key','角色 key','公司內穩定 RBAC 角色 key','string',false,'immutable','normal','role_key','[]','{}',10),
          ('iam.role','name','角色名','RBAC 訪問角色顯示名稱','string',false,'adapter_only','normal','name','[]','{}',20),
          ('iam.role','level','角色級別','RBAC 訪問角色級別','integer',false,'adapter_only','normal','level','[]','{"minimum":"1","maximum":"10"}',30),
          ('iam.role','active','啟用','RBAC 訪問角色是否有效','boolean',false,'adapter_only','normal','active','[]','{}',40),
          ('iam.role','permissions','權限集合','角色的完整權限 key 集合','array',false,'adapter_only','confidential','permissions','[]','{}',50),
          ('iam.role','updated_at','更新時間','角色或權限集合最近更新時間','datetime',false,'derived','normal','updated_at','[]','{}',60)
        ON CONFLICT (resource_key,field_key) DO UPDATE SET
          label=EXCLUDED.label,
          semantic_description=EXCLUDED.semantic_description,
          data_type=EXCLUDED.data_type,
          nullable=EXCLUDED.nullable,
          editable_mode=EXCLUDED.editable_mode,
          sensitivity=EXCLUDED.sensitivity,
          storage_column=EXCLUDED.storage_column,
          constraints=EXCLUDED.constraints,
          display_order=EXCLUDED.display_order,
          active=true;

        INSERT INTO app.resource_relations(
          relation_key,source_resource_key,target_resource_key,
          source_field_key,target_field_key,cardinality,semantic_description
        ) VALUES
          ('iam.member.primary_position','iam.member','iam.position_profile','position_code','position_code','many_to_one','成員主崗位必須是同一公司的真實崗位'),
          ('iam.member.primary_department','iam.member','iam.organizational_unit','department_code','unit_code','many_to_one','成員部門由同一公司的主崗位推導')
        ON CONFLICT (relation_key) DO UPDATE SET
          semantic_description=EXCLUDED.semantic_description,
          active=true;

        INSERT INTO app.resource_invariants(
          invariant_key,resource_key,description,enforcement,machine_contract
        ) VALUES
          (
            'iam.member.provisioning_adapter','iam.member',
            '成員建立必須原子寫入全局身份、公司成員與主崗位，並回讀驗證；不得用通用資料寫入器建立登入帳號',
            'domain_adapter',
            jsonb_build_object(
              'adapter','user_add_or_user_import','transaction','all_or_nothing',
              'password','hash_only','readback',true
            )
          ),
          (
            'iam.member.position_role_separation','iam.member',
            '組織崗位不得隱式轉換成 RBAC 訪問角色，只有明確 access_role 才能授權',
            'domain_adapter',
            jsonb_build_object(
              'position','organization_topology','access_role','explicit_rbac_only'
            )
          ),
          (
            'iam.role.canonical_adapter','iam.role',
            'RBAC 角色及權限必須寫入 iam.roles 與 iam.role_permissions 並回讀驗證',
            'domain_adapter',
            jsonb_build_object('adapter','role_upsert_or_role_update','readback',true)
          )
        ON CONFLICT (invariant_key) DO UPDATE SET
          description=EXCLUDED.description,
          enforcement=EXCLUDED.enforcement,
          machine_contract=EXCLUDED.machine_contract,
          active=true;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key IN (
          'iam.member.provisioning_adapter',
          'iam.member.position_role_separation',
          'iam.role.canonical_adapter'
        );
        DELETE FROM app.resource_relations
        WHERE relation_key IN (
          'iam.member.primary_position','iam.member.primary_department'
        );
        DELETE FROM app.resource_types WHERE resource_key IN ('iam.member','iam.role');
        UPDATE app.resource_types SET aliases='[]'::jsonb
        WHERE resource_key IN ('iam.organizational_unit','iam.position_profile');
        DROP VIEW IF EXISTS iam.role_directory;
        DROP VIEW IF EXISTS iam.member_directory;
        DROP INDEX IF EXISTS app.idx_resource_types_aliases;
        ALTER TABLE app.resource_types DROP CONSTRAINT IF EXISTS resource_types_aliases_array;
        ALTER TABLE app.resource_types DROP COLUMN IF EXISTS aliases;
        """
    )
