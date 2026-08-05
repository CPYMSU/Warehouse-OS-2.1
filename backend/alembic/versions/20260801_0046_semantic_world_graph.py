"""Expand the AI-native semantic world graph for digital-asset hosting.

Revision ID: 20260801_0046
Revises: 20260801_0045
Create Date: 2026-08-01
"""

from __future__ import annotations

from alembic import op

revision = "20260801_0046"
down_revision = "20260801_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO app.resource_types(
          resource_key, label, description, storage_schema, storage_table,
          version_column, version_strategy, identity_fields, allowed_effects
        ) VALUES
          ('digital_asset.asset_version','資產版本','資產可部署或可驗證的版本與來源','digital_asset','asset_versions',NULL,'none','["id","legacy_id","version_no"]','["read","query"]'),
          ('digital_asset.artifact','托管附件','內容尋址的源碼、包、資料、模型或文件附件','digital_asset','artifacts',NULL,'none','["id","sha256","object_key"]','["read","query"]'),
          ('digital_asset.component','工作區組件','前端、後端、Worker 或 Agent 的可配置組件','digital_asset','workspace_components','updated_at','timestamp','["id","component_name"]','["read","query","update"]'),
          ('digital_asset.storage_binding','儲存綁定','工作區的物件儲存提供者及可觀察狀態','digital_asset','storage_bindings','updated_at','timestamp','["id","object_prefix"]','["read","query"]'),
          ('digital_asset.database_binding','資料庫綁定','工作區的邏輯資料庫、隔離模式與 Data API 狀態','digital_asset','database_bindings','updated_at','timestamp','["id","logical_name"]','["read","query"]'),
          ('digital_asset.api_credential','工作區 API Key','只暴露 Key 類型、作用域與生命週期，不暴露明文或雜湊','digital_asset','api_credentials','issued_at','timestamp','["id","token_hint","label"]','["read","query"]'),
          ('digital_asset.deployment','部署觀察','來源版本、組件、提供者、健康與公開網址的真實部署觀察','digital_asset','deployments','updated_at','timestamp','["id","legacy_id"]','["read","query"]')
        ON CONFLICT (resource_key) DO UPDATE SET
          label = EXCLUDED.label,
          description = EXCLUDED.description,
          identity_fields = EXCLUDED.identity_fields,
          allowed_effects = EXCLUDED.allowed_effects,
          active = true;

        INSERT INTO app.resource_fields(
          resource_key, field_key, label, semantic_description, data_type,
          nullable, editable_mode, sensitivity, storage_column, json_path,
          constraints, display_order
        ) VALUES
          ('digital_asset.asset','id','資產 UUID','跨能力持續使用的資產主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.asset','legacy_id','資產數字 ID','舊介面相容識別碼','integer',false,'immutable','normal','legacy_id','[]','{}',2),

          ('digital_asset.workspace','id','工作區 UUID','跨能力持續使用的工作區主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.workspace','legacy_id','工作區數字 ID','舊介面相容識別碼','integer',false,'immutable','normal','legacy_id','[]','{}',2),
          ('digital_asset.workspace','asset_id','所屬資產 UUID','工作區所屬的唯一資產主鍵','uuid',false,'immutable','normal','asset_id','[]','{}',3),

          ('digital_asset.asset_version','id','版本 UUID','版本主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.asset_version','legacy_id','版本數字 ID','舊介面相容識別碼','integer',false,'immutable','normal','legacy_id','[]','{}',2),
          ('digital_asset.asset_version','asset_id','所屬資產','版本所屬資產 UUID','uuid',false,'immutable','normal','asset_id','[]','{}',3),
          ('digital_asset.asset_version','version_no','版本號','資產內的穩定版本標識','string',false,'immutable','normal','version_no','[]','{}',10),
          ('digital_asset.asset_version','title','版本標題','版本用途或內容說明','string',true,'adapter_only','normal','title','[]','{}',20),
          ('digital_asset.asset_version','artifact_uri','來源位置','源碼或交付物的托管 URI','string',true,'adapter_only','confidential','artifact_uri','[]','{}',30),
          ('digital_asset.asset_version','artifact_sha256','內容雜湊','可驗證交付物 SHA-256','string',true,'immutable','normal','artifact_sha256','[]','{}',40),
          ('digital_asset.asset_version','created_at','建立時間','版本建立時間','datetime',false,'immutable','normal','created_at','[]','{}',50),

          ('digital_asset.artifact','id','附件 UUID','托管附件主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.artifact','asset_id','所屬資產','附件所屬資產 UUID','uuid',false,'immutable','normal','asset_id','[]','{}',2),
          ('digital_asset.artifact','version_id','所屬版本','可空的資產版本 UUID','uuid',true,'immutable','normal','version_id','[]','{}',3),
          ('digital_asset.artifact','artifact_kind','附件類型','source、package、document 等托管類型','string',false,'immutable','normal','artifact_kind','[]','{}',10),
          ('digital_asset.artifact','filename','文件名','用戶可見文件名','string',true,'immutable','normal','filename','[]','{}',20),
          ('digital_asset.artifact','size_bytes','大小','附件位元組數','integer',false,'immutable','normal','size_bytes','[]','{}',30),
          ('digital_asset.artifact','sha256','SHA-256','內容驗證雜湊','string',false,'immutable','normal','sha256','[]','{}',40),
          ('digital_asset.artifact','storage_provider','儲存提供者','服務端儲存綁定名稱','string',false,'immutable','normal','storage_provider','[]','{}',50),
          ('digital_asset.artifact','object_key','物件鍵','服務端物件定位鍵','string',false,'immutable','confidential','object_key','[]','{}',60),
          ('digital_asset.artifact','state','托管狀態','stored、verified、quarantined 等觀察狀態','string',false,'derived','normal','state','[]','{}',70),

          ('digital_asset.component','id','組件 UUID','工作區組件主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.component','workspace_id','所屬工作區','組件所屬工作區 UUID','uuid',false,'immutable','normal','workspace_id','[]','{}',2),
          ('digital_asset.component','source_version_id','來源版本','目前綁定的資產版本 UUID','uuid',true,'adapter_only','normal','source_version_id','[]','{}',3),
          ('digital_asset.component','component_name','組件名稱','工作區內穩定組件名稱','string',false,'immutable','normal','component_name','[]','{}',10),
          ('digital_asset.component','component_kind','組件類型','frontend、backend、worker 或 agent','string',false,'adapter_only','normal','component_kind','[]','{}',20),
          ('digital_asset.component','runtime','運行時','python3.12、node20、static 等配置','string',false,'direct','normal','runtime','[]','{}',30),
          ('digital_asset.component','entrypoint','入口文件','應用入口文件','string',true,'direct','normal','entrypoint','[]','{}',40),
          ('digital_asset.component','build_command','構建命令','構建階段命令','string',true,'direct','confidential','build_command','[]','{}',50),
          ('digital_asset.component','start_command','啟動命令','運行階段命令','string',true,'direct','confidential','start_command','[]','{}',60),
          ('digital_asset.component','status','組件狀態','由構建與運行適配器觀察','string',false,'derived','normal','status','[]','{}',70),

          ('digital_asset.storage_binding','id','儲存綁定 UUID','儲存綁定主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.storage_binding','workspace_id','所屬工作區','儲存綁定所屬工作區 UUID','uuid',false,'immutable','normal','workspace_id','[]','{}',2),
          ('digital_asset.storage_binding','provider_key','提供者','儲存提供者 key','string',false,'immutable','normal','provider_key','[]','{}',10),
          ('digital_asset.storage_binding','object_prefix','物件前綴','工作區隔離物件前綴','string',false,'immutable','confidential','object_prefix','[]','{}',20),
          ('digital_asset.storage_binding','status','狀態','儲存提供者可觀察狀態','string',false,'derived','normal','status','[]','{}',30),

          ('digital_asset.database_binding','id','資料庫綁定 UUID','資料庫綁定主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.database_binding','workspace_id','所屬工作區','資料庫所屬工作區 UUID','uuid',false,'immutable','normal','workspace_id','[]','{}',2),
          ('digital_asset.database_binding','logical_name','邏輯名稱','應用使用的可攜式資料庫名稱','string',false,'immutable','normal','logical_name','[]','{}',10),
          ('digital_asset.database_binding','engine','引擎','PostgreSQL 等資料庫引擎','string',false,'immutable','normal','engine','[]','{}',20),
          ('digital_asset.database_binding','provider_key','提供者','平台資料提供者 key','string',false,'immutable','normal','provider_key','[]','{}',30),
          ('digital_asset.database_binding','isolation_mode','隔離模式','workspace_rls、dedicated_schema 等','string',false,'adapter_only','normal','isolation_mode','[]','{}',40),
          ('digital_asset.database_binding','status','狀態','資料庫提供者可觀察狀態','string',false,'derived','normal','status','[]','{}',50),
          ('digital_asset.database_binding','endpoint_ref','端點引用','不含 DSN 的平台端點引用','string',false,'immutable','confidential','endpoint_ref','[]','{}',60),

          ('digital_asset.api_credential','id','憑證 UUID','Key 記錄主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.api_credential','workspace_id','所屬工作區','Key 所屬工作區 UUID','uuid',false,'immutable','normal','workspace_id','[]','{}',2),
          ('digital_asset.api_credential','label','標籤','Key 的用途標籤','string',false,'immutable','normal','label','[]','{}',10),
          ('digital_asset.api_credential','token_hint','Key 提示','只顯示末段的非敏感提示','string',false,'immutable','normal','token_hint','[]','{}',20),
          ('digital_asset.api_credential','scopes','作用域','Key 可調用的工作區能力','array',false,'immutable','confidential','scopes','[]','{}',30),
          ('digital_asset.api_credential','key_kind','Key 類型','primary 或 delegated','string',false,'immutable','normal','key_kind','[]','{}',40),
          ('digital_asset.api_credential','issued_at','簽發時間','Key 簽發時間','datetime',false,'immutable','normal','issued_at','[]','{}',50),
          ('digital_asset.api_credential','expires_at','到期時間','可空的 Key 到期時間','datetime',true,'immutable','normal','expires_at','[]','{}',60),
          ('digital_asset.api_credential','last_used_at','最後使用','最近一次成功使用時間','datetime',true,'derived','normal','last_used_at','[]','{}',70),
          ('digital_asset.api_credential','revoked_at','撤銷時間','存在即表示 Key 已撤銷','datetime',true,'derived','normal','revoked_at','[]','{}',80),

          ('digital_asset.deployment','id','部署 UUID','部署主鍵','uuid',false,'immutable','normal','id','[]','{}',1),
          ('digital_asset.deployment','legacy_id','部署數字 ID','舊介面相容識別碼','integer',false,'immutable','normal','legacy_id','[]','{}',2),
          ('digital_asset.deployment','workspace_id','所屬工作區','部署所屬工作區 UUID','uuid',false,'immutable','normal','workspace_id','[]','{}',3),
          ('digital_asset.deployment','component_id','所屬組件','部署組件 UUID','uuid',true,'immutable','normal','component_id','[]','{}',4),
          ('digital_asset.deployment','source_version_id','來源版本','部署使用的資產版本 UUID','uuid',true,'immutable','normal','source_version_id','[]','{}',5),
          ('digital_asset.deployment','revision','修訂','組件內單調增加的部署修訂','integer',false,'immutable','normal','revision','[]','{}',10),
          ('digital_asset.deployment','provider_key','運行提供者','實際接手部署的提供者','string',false,'derived','normal','provider_key','[]','{}',20),
          ('digital_asset.deployment','status','部署狀態','queued、building、deploying、ready 或 failed','string',false,'derived','normal','status','[]','{}',30),
          ('digital_asset.deployment','health','健康','由運行探活得到的健康狀態','string',false,'derived','normal','health','[]','{}',40),
          ('digital_asset.deployment','public_url','公開網址','部署提供者實際返回的網址','string',true,'derived','normal','public_url','[]','{}',50),
          ('digital_asset.deployment','created_at','建立時間','部署請求建立時間','datetime',false,'immutable','normal','created_at','[]','{}',60)
        ON CONFLICT (resource_key, field_key) DO UPDATE SET
          label = EXCLUDED.label,
          semantic_description = EXCLUDED.semantic_description,
          editable_mode = EXCLUDED.editable_mode,
          sensitivity = EXCLUDED.sensitivity,
          active = true;

        INSERT INTO app.resource_relations(
          relation_key, source_resource_key, target_resource_key,
          source_field_key, target_field_key, cardinality, semantic_description
        ) VALUES
          ('digital_asset.asset_version.belongs_to_asset','digital_asset.asset_version','digital_asset.asset','asset_id','id','many_to_one','版本屬於同一租戶的一個數字資產'),
          ('digital_asset.artifact.belongs_to_asset','digital_asset.artifact','digital_asset.asset','asset_id','id','many_to_one','附件屬於同一租戶的一個數字資產'),
          ('digital_asset.artifact.belongs_to_version','digital_asset.artifact','digital_asset.asset_version','version_id','id','many_to_one','附件可連結到同一資產的一個版本'),
          ('digital_asset.component.belongs_to_workspace','digital_asset.component','digital_asset.workspace','workspace_id','id','many_to_one','組件屬於一個工作區'),
          ('digital_asset.component.uses_version','digital_asset.component','digital_asset.asset_version','source_version_id','id','many_to_one','組件可綁定一個來源版本'),
          ('digital_asset.storage_binding.belongs_to_workspace','digital_asset.storage_binding','digital_asset.workspace','workspace_id','id','one_to_one','儲存綁定屬於一個工作區'),
          ('digital_asset.database_binding.belongs_to_workspace','digital_asset.database_binding','digital_asset.workspace','workspace_id','id','many_to_one','資料庫綁定屬於一個工作區'),
          ('digital_asset.api_credential.belongs_to_workspace','digital_asset.api_credential','digital_asset.workspace','workspace_id','id','many_to_one','API Key 屬於一個工作區'),
          ('digital_asset.deployment.belongs_to_workspace','digital_asset.deployment','digital_asset.workspace','workspace_id','id','many_to_one','部署屬於一個工作區'),
          ('digital_asset.deployment.belongs_to_component','digital_asset.deployment','digital_asset.component','component_id','id','many_to_one','部署可指向一個工作區組件'),
          ('digital_asset.deployment.uses_version','digital_asset.deployment','digital_asset.asset_version','source_version_id','id','many_to_one','部署可使用一個資產版本')
        ON CONFLICT (relation_key) DO UPDATE SET
          semantic_description = EXCLUDED.semantic_description,
          active = true;

        INSERT INTO app.resource_invariants(
          invariant_key, resource_key, description, enforcement, machine_contract
        ) VALUES
          ('digital_asset.deployment.external_reality','digital_asset.deployment','ready、health 與 public_url 必須來自部署提供者或探活證據，通用資料修改不可偽造','external_verification','{"fields":["status","health","public_url"]}'),
          ('digital_asset.api_credential.secret_redaction','digital_asset.api_credential','語義世界只顯示 Key 提示與生命週期，永不顯示明文或 token_hash','database','{"hidden_fields":["token_hash"]}'),
          ('digital_asset.artifact.immutable_custody','digital_asset.artifact','已托管附件的內容身份不可用通用更新改寫','domain_adapter','{"immutable_fields":["asset_id","sha256","object_key"]}')
        ON CONFLICT (invariant_key) DO UPDATE SET
          description = EXCLUDED.description,
          machine_contract = EXCLUDED.machine_contract,
          active = true;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM app.resource_invariants
        WHERE invariant_key IN (
          'digital_asset.deployment.external_reality',
          'digital_asset.api_credential.secret_redaction',
          'digital_asset.artifact.immutable_custody'
        );
        DELETE FROM app.resource_relations
        WHERE relation_key IN (
          'digital_asset.asset_version.belongs_to_asset',
          'digital_asset.artifact.belongs_to_asset',
          'digital_asset.artifact.belongs_to_version',
          'digital_asset.component.belongs_to_workspace',
          'digital_asset.component.uses_version',
          'digital_asset.storage_binding.belongs_to_workspace',
          'digital_asset.database_binding.belongs_to_workspace',
          'digital_asset.api_credential.belongs_to_workspace',
          'digital_asset.deployment.belongs_to_workspace',
          'digital_asset.deployment.belongs_to_component',
          'digital_asset.deployment.uses_version'
        );
        DELETE FROM app.resource_types
        WHERE resource_key IN (
          'digital_asset.asset_version', 'digital_asset.artifact',
          'digital_asset.component', 'digital_asset.storage_binding',
          'digital_asset.database_binding', 'digital_asset.api_credential',
          'digital_asset.deployment'
        );
        DELETE FROM app.resource_fields
        WHERE (resource_key = 'digital_asset.asset' AND field_key IN ('id','legacy_id'))
           OR (resource_key = 'digital_asset.workspace' AND field_key IN ('id','legacy_id','asset_id'));
        """
    )
