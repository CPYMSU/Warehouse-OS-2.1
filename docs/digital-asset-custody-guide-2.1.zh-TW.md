# Warehouse OS 2.1《數字資產託管指南》

> 適用版本：Warehouse OS 2.1<br>
> 契約日期：2026-08-02<br>
> 控制面基線：PostgreSQL 18、強制 Row Level Security（RLS）、`wak_` 工作區 Key、`/api/workspaces/v1/*`；工作區應用資料庫可自選<br>
> 適用對象：在 Warehouse OS 登記、託管、開發或維護數字資產的企業管理員與開發者

## 0. 給終端 AI：優先使用智能託管接口

外部 AI、使用者自己的終端 AI 及 Warehouse AI 秘書不需要自行拼接資產、儲存、源碼、Runtime、部署與激活接口。先下載智能工具包：

```text
GET /api/hosting/v2/kit
GET /api/hosting/v2/manifest
GET /api/hosting/v2/dm.py
GET /api/hosting/v2/dm-guide.md
GET /api/hosting/v2/developer-standard.md
GET /api/hosting/v2/contract.json
```

`wak_` 工作區 Key 可以直接使用這組接口，但永遠只能操作 Key 所屬的公司與工作區。推薦流程：

```bash
export WAREHOUSE_BASE_URL="https://bonfirework.org"
export WAREHOUSE_WORKSPACE_KEY="wak_..."
python3 dm.py agent manifest
python3 dm.py hosting requirements
python3 dm.py agent start \
  --message "判斷這個項目的 Runtime 並部署到 healthy" \
  --desired-state '{"runtime":{"type":"auto"},"deployment":{"state":"ready"}}'
python3 dm.py agent source <session_id> source.tar.gz --version v1.0.0
python3 dm.py agent say <session_id> \
  --message "源碼已上傳，繼續直到 ready" \
  --desired-state '{"runtime":{"type":"auto"},"deployment":{"state":"ready"}}' \
  --execute
python3 dm.py agent status <session_id>
python3 dm.py agent events <session_id>
```

自然語言 `message` 用於人與 AI 溝通，`desired_state` 是可驗證的目標，不是固定工作流。服務端會根據真實源碼訊號選擇 static、web、api、worker 或 agent，執行 HDD/SSD 寫入探針，提交部署並持續返回結構化事件。失敗時同一會話會保留 `stage`、`component`、`error_code`、HTTP 狀態、原始安全錯誤、是否可恢復及下一步；修復後應續用原 `session_id`，避免重建資產或工作區。

底層 `/api/workspaces/v1/*` 仍是權威原子能力，供進階客戶端使用；一般終端 AI 應優先使用 `/api/hosting/v2/*`。

## 1. 先理解四個獨立對象

Warehouse OS 2.1 不把「上傳一個檔案」當成完整託管。資產、工作區、永久入口與實際部署各自有獨立狀態：

| 對象 | 真實含義 |
|---|---|
| 數字資產 | 名稱、類型、版本、交付物、SHA-256 與雜湊鏈託管事件 |
| 工作區 | 綁定前端、後端、Worker 或 Agent 組件，以及儲存、數據庫、Key 和部署記錄 |
| 永久入口 | 建立工作區時立即保留的 `/assets/{tenant_slug}/{workspace_key}/`；未部署時顯示真實狀態頁 |
| 已部署應用 | 只有部署狀態為 `ready`、健康狀態為 `healthy` 且有經驗證的應用 URL 時才成立 |
| PostgreSQL Data API | 選用的平台資料服務；工作區也可自管其他資料引擎或不使用資料庫 |
| `wak_` 工作區 Key | 只代表一個租戶內的一個工作區，並帶有明確作用域與到期時間 |

永久入口固定不變。應用尚未上線時，它顯示工作區狀態、Runtime、源碼狀態和儲存用量；應用真正上線後，入口才會跳轉到通過健康核驗的應用 URL。`public_url`、排隊記錄或永久入口本身都不能單獨證明應用已部署。

內部 UUID、租戶 ID、數據庫 DSN、主機路徑、內部端口和提供者憑證都由服務端決定。客戶端不得提交或猜測這些值。

## 2. 目前能力邊界

| 能力 | 目前狀態 |
|---|---|
| 資產、版本、交付物與託管事件 | 可用 |
| 永久工作區入口 | 可用；建立工作區即保留 |
| 工作區儲存配額 | 可用；初始固定 512 MiB，之後每次只增加 512 MiB |
| 本機內容定址物件儲存 | 開發提供者可用；寫入時由服務端復算 SHA-256 |
| PostgreSQL/RLS Data API | 可選；平台代管模式可用 |
| 工作區自管資料庫 | 可用；受限 Compose、工作區命名卷與 Secret，可選任意資料引擎 |
| 主／附屬工作區 Key、輪換與吊銷 | 可用 |
| HDD 工作區獨立 PostgreSQL 數據庫 | 可用；DSN 不向客戶端或 AI 暴露 |
| 工作區源碼與部署 API | 可用；`wak_` 的 deploy/logs scope 對應真實 API |
| 應用 Runtime | 可用；Runtime Controller 領取 queue、驗證源碼、健康探測後切換永久入口 |

2.1 不提供舊系統的 SQLite 工作區、raw SQL 客戶端、`dak_` Key、`/api/dam/v1/*` 或 `db exec`。源碼 push、部署觀察與 verified revision 切換改由 `/api/workspaces/v1/*` 原生契約提供。

## 3. 最快開通方式

### 3.1 一次建立資產、工作區、Data API 與主 Key

在 Warehouse OS 終端或 AI 秘書中執行：

```text
dm provision --name "客戶營運系統" --kind software --runtime api --workspace-key customer-operations
```

這個命令會在目前公司內依次建立：

1. 數字資產與首筆雜湊鏈託管事件；
2. 工作區、永久入口及需要的組件；
3. 初始 512 MiB 儲存配額；
4. `warehouse_postgresql_data_api` 數據庫綁定；
5. 一把唯一的主 `wak_` 工作區 Key。

常用選項：

```text
--summary "用途說明"
--plan custody|hosted|managed|dedicated
--runtime static|web|api|worker|agent
--database app
--label "正式環境主 Key"
--expires-days 90
```

`--plan custody` 只建立保管工作區，不建立 Data API 綁定。這種工作區的 Key 可執行 `info`，但不能執行 `schema`、`list` 或 `put`。其他計畫預設建立可攜式 `workspace_rls` Data API；請勿把 `dedicated` 計畫誤解為專用數據庫提供者已經完成。

同一資產與同一 `workspace_key` 的工作區建立具有冪等語義：已存在時返回既有工作區，不重複建立。若同一 Key 已屬於其他資產，服務端返回 HTTP 409。

### 3.2 Passkey、Keychain 與一次性明文交付

在 AI 秘書中，受保護命令先建立待授權操作卡，不會在討論或規劃階段直接修改資料。Passkey 只簽署卡片中的精確操作清單，並產生綁定公司、帳號、會話、工具和參數摘要的一次性 Keychain；確認接口本身不執行業務代碼。

AI Runtime 收到授權信號後才領取並消耗 Keychain、執行操作和核對結果。`wak_` 明文透過綁定目前瀏覽器頁籤的 15 分鐘一次性安全卡交付，不會寫入聊天、執行快照或審計日誌。領取後請立即存入密碼管理器並點擊安全清除；明文被清除後不能找回，只能輪換或重新簽發。

### 3.3 永久入口與工作區配額

工作區建立後立即取得：

```text
https://你的Warehouse網域/assets/{tenant_slug}/{workspace_key}/
```

新工作區的正式儲存配額固定為 512 MiB，建立時不能要求其他容量。需要擴容時，每次只能增加一個 512 MiB 單位：

```text
dm workspace resize --id <資產 UUID、DMA 編號或名稱> \
  --workspace customer-operations \
  --delta-mb 512
```

也可以用下一個總容量表示，但必須剛好等於目前容量加 512 MiB：

```text
dm workspace resize --id <資產> --workspace customer-operations --target-mb 1024
```

`delta-mb` 與 `target-mb` 必須二選一。建議同時提交目前工作區的 `expected-revision`；版本不一致時服務端返回 HTTP 409，避免併發操作覆蓋。配額只能增加，不能藉此縮減；每次變更都寫入審計。

核心代碼建立時預設 HDD；使用者明確指定時可用 SSD。在尚未存在任何源碼版本或 `code` 工件的空工作區，可以原地改變代碼儲存綁定：

```text
dm workspace storage --workspace customer-operations --code-storage ssd
```

這個動作保留同一工作區 UUID、Key 與永久入口，只更新 code binding，不做實體複製，也不改動 DATA 或數據庫的 HDD 綁定。若已有源碼／代碼工件，服務端返回 HTTP 409 `code_storage_migration_required`；此時 AI 必須提出包含複製、雜湊校驗、切換與回滾證據的遷移方案，不能只改資料庫欄位宣稱完成。

### 3.4 主 Key 與附屬 Key

每個工作區只有一把活動中的主 Key。主 Key 固定擁有 `workspace:read`、`data:read`、`data:write`、`deploy:read`、`deploy:write`、`logs:read` 全部作用域，不能用普通吊銷接口刪除。替換主 Key 必須原子輪換：

```text
dm key primary rotate --workspace customer-operations --expires-days 90
```

輪換會立即撤銷舊主 Key，但不影響既有附屬 Key。為協作者、程序或環境簽發獨立附屬 Key：

```text
dm key issue --workspace customer-operations \
  --label "資料匯入服務" \
  --scopes workspace:read,data:read,data:write \
  --expires-days 30
```

附屬 Key 預設只有 `workspace:read,data:read`。每把附屬 Key 都保留簽發時的父主 Key 記錄，但主 Key 輪換後仍可繼續使用。

列出安全元資料或吊銷單一附屬 Key：

```text
dm key list --workspace customer-operations
dm key revoke --workspace customer-operations --key-id <憑證 UUID>
```

列表只返回 UUID、主／附屬類型、父 Key、label、hint、作用域、簽發／到期／最近使用／吊銷時間，不返回明文或 token hash。附屬 Key 吊銷立即生效；重複吊銷是冪等操作。

### 3.5 Runtime 升級不是部署完成

若工作區最初是 `static`，之後需要後端，應使用真實 `workspace_key` 原地升級：

```text
dm runtime upgrade --workspace mk4-workspace \
  --type web \
  --runtime node20 \
  --start-command "npm start"
```

這會把 Runtime 類型改為 `web` 或 `api`，並建立或更新 backend 組件。只有已存在受託管源碼版本時才會建立部署請求；沒有源碼時返回 `upload_source_and_create_version`。`queued` 只表示請求已持久化，`building` 也不代表健康核驗完成。只有 `ready`、`healthy` 與經驗證的應用 URL 同時成立，才能稱為已上線。

## 4. 下載與設定 dam.py 2.1

`dam.py` 是工作區資料面與部署資料面的客戶端，不是公司控制面管理工具。它不負責建立資產、擴容或簽發 Key；持有相應 scope 時可以上傳源碼、提交部署、查看事件／日誌及切換既有 healthy revision。

```bash
curl -o dam.py https://你的Warehouse網域/api/digital-assets/cli
python dam.py --version
```

用環境變數提供服務地址和工作區 Key：

```bash
export WAREHOUSE_BASE_URL="https://你的Warehouse網域"
export WAREHOUSE_WORKSPACE_KEY="wak_你的工作區Key"
```

先驗證身份與工作區：

```bash
python dam.py info
python dam.py storage probe
```

`info` 只顯示這把 Key 所屬的工作區、組件、數據庫、作用域和 Key 標籤，不返回 Key 明文、token hash、DSN 或其他公司的資料。`storage probe` 會修復舊工作區遺失的 code/data 綁定，並對選定 provider 實際完成 create、write、fsync、read-back、delete；只有全部通過才標記為 `ready`。

### 4.1 上傳不可變源碼與部署

```bash
python dam.py source push ./app.zip --version v1.0.0 --component api
python dam.py source list
python dam.py runtime set --type auto --source <source-version-uuid>
python dam.py deploy request --source <source-version-uuid> --component api
python dam.py deploy status <deployment-uuid>
python dam.py deploy logs <deployment-uuid>
```

源碼必須是 ZIP 或 TAR。服務端復算 SHA-256，拒絕絕對路徑、`..`、link、特殊文件、過多項目與解壓炸彈，再以同一交易建立 artifact、asset version 與 custody event。部署 request 只返回 `queued`；Runtime Controller 完成內部及永久入口健康探測後才返回 `ready/healthy`。

`runtime set` 接受 `auto/static/web/api/worker/agent/container/compose`。`auto` 以受驗證壓縮包的實際證據選擇資料庫中的 Runtime profile；也可用 `--runtime python3.12`、`--runtime node20`、`--entrypoint`、`--start-command` 覆寫。加上 `--deploy` 可在同一原子呼叫配置組件並提交部署；worker/agent 以持續運行程序核驗，不會偽造網站 URL。

切換到任何既有 healthy revision（包含回滾）使用：

```bash
python dam.py deploy activate <deployment-uuid>
```

### 4.2 同一把 Key 的 Hosting Fabric

`dm.py 2.3` 把高級託管能力收斂為聲明式資源，不要求終端 AI 記住十套流程：

```bash
python dm.py fabric manifest
python dm.py fabric show
python dm.py fabric apply <kind> --spec-file resource.json \
  --idempotency-key stable-operation-key
python dm.py fabric action <action-uuid>
```

主 Key 擁有全部工作區作用域；附屬 Key 可只授予需要的 `infra:read`、`infra:write`、`domain:write`、`secrets:write`、`database:admin`、`repository:write`、`backup:write` 或 `accelerator:use`。每次 apply 都保存 desired state、observed state、不可變事件與精確錯誤。外部供應商未配置時返回 durable `blocked`，不會把「已記錄」冒充「已生效」。

常見資源 spec：

```json
{"kind":"environment","spec":{"component":"api","variables":{"APP_MODE":"production"}}}
{"kind":"secret","spec":{"name":"MODEL_API_TOKEN","value":"只寫明文","component":"api"}}
{"kind":"scaling","spec":{"component":"api","min_replicas":2,"max_replicas":6,"target_cpu_percent":65}}
{"kind":"domain","spec":{"hostname":"app.example.com","redirect_https":true}}
{"kind":"repository","spec":{"url":"https://github.com/example/app.git","ref":"main","credential_secret":"GIT_TOKEN","auto_sync":true,"sync_interval_seconds":300}}
{"kind":"database_migration","spec":{"version":"2026.08.03.1","sql":"CREATE TABLE app.jobs(id uuid PRIMARY KEY)"}}
{"kind":"backup","spec":{"action":"create","mode":"logical","destination":"local","retention_days":30}}
{"kind":"accelerator","spec":{"kind":"gpu","count":1,"memory_mb":16384,"required":true}}
```

秘密明文只可直接送到 `/api/workspaces/v1/fabric/resources` 或 `dm.py fabric apply secret`，不會寫入 AI 對話、資源 desired state、action request 或任何讀取回應。Runtime 啟動時才在記憶體解密並注入指定組件。

任意 Dockerfile 可用：

```bash
python dm.py runtime set --type container --source <source-uuid> \
  --dockerfile Dockerfile --port 8080 --health-path /health --deploy
```

Compose 可編排最多 16 個服務；對外路由服務與一般容器都可有 1–8 個副本，Runtime Worker 會讀取 one-shot CPU／記憶體指標，依資料庫中的 min/max/target/cooldown 策略動態增減健康副本，永久入口以穩定請求雜湊及故障轉移分流。平台拒絕 `privileged`、host network、host PID/IPC、devices、cap_add、Docker socket 與主機路徑；持久資料只能寫入該工作區 HDD data volume。

資料庫 migration 只在該工作區專屬、非 superuser 的 PostgreSQL role 內以交易執行，拒絕角色／數據庫管理、主機文件 COPY、GRANT／REVOKE 及系統 schema 修改。版本與 SHA-256 寫入不可變歷史，同版本不同校驗值會被拒絕。

Git 同步只接受無憑證 HTTPS URL，先阻擋回環、私網與保留地址，再 shallow clone、移除 `.git`、由服務端驗證歸檔並建立不可變 source version。私有倉庫的 token 必須先保存成 secret，再以名稱引用。設定 `auto_sync=true` 後，Runtime Controller 按資料庫中的 `sync_interval_seconds`（60–86400 秒）自動重拉；相同內容以 SHA-256 冪等復用，不重複佔用配額。

自訂網域先取得全平台唯一 hostname claim，再交由受限主機代理配置 Nginx 與 ACME。平台主域及其子域不可由工作區 Key 佔用；其他工作區或既有 Nginx 站點已持有同一 hostname 時會返回可診斷的 `blocked/409`，不會覆蓋原站點。

本機 logical backup／同工作區 restore 可直接執行。平台使用每工作區獨立、不可登入且可跨越 FORCE RLS 的備份身份；Runtime 永遠維持 NOBYPASSRLS 且不能切換到備份身份。ready 證據包括 owner 保留、校驗和、臨時庫恢復，以及 FORCE RLS relation 的逐表源／恢復行數一致。PITR 或異地備份也使用相同 `backup` 資源，但只有服務器接入 WAL archive、base backup、timeline restore 或加密遠端 object store 後才會成為 ready；未接入時 action 會明確 blocked 並列出缺少的 provider capability。GPU 同理：只有 Runtime Worker 實測到可分配 GPU 池才會分配並向 Docker 注入 DeviceRequest。

## 5. 使用 PostgreSQL Data API

### 5.1 查看集合結構

```bash
python dam.py schema
python dam.py schema --database app_customer_operations
```

Data API 使用「集合＋記錄鍵＋JSON 物件」模型，不接受客戶端 raw SQL。

### 5.2 建立或更新記錄

新記錄建議帶 `--expected-version 0`，避免意外覆蓋：

```bash
python dam.py put customers acme \
  --data '{"name":"Acme","active":true}' \
  --expected-version 0
```

也可以從 JSON 文件或 stdin 讀取：

```bash
python dam.py put orders order-1001 --file order.json --expected-version 0
printf '%s' '{"status":"draft"}' | python dam.py put orders order-1002 --file - --expected-version 0
```

### 5.3 分頁讀取與樂觀併發

```bash
python dam.py list customers --limit 100 --offset 0
```

每筆記錄都帶 `version`。更新時使用剛讀到的版本：

```bash
python dam.py put customers acme \
  --data '{"name":"Acme","active":false}' \
  --expected-version 1
```

如果其他程序已先更新，服務端返回 HTTP 409。請重新讀取、合併變更後再提交，不要移除版本條件強行覆蓋。

## 6. 直接呼叫工作區資料面 API

所有請求使用同一個 Bearer Header：

```http
Authorization: Bearer wak_<signed-token>
```

```bash
# 工作區資訊
curl -sS \
  -H "Authorization: Bearer $WAREHOUSE_WORKSPACE_KEY" \
  "$WAREHOUSE_BASE_URL/api/workspaces/v1/info"

# 資料結構
curl -sS \
  -H "Authorization: Bearer $WAREHOUSE_WORKSPACE_KEY" \
  "$WAREHOUSE_BASE_URL/api/workspaces/v1/database/schema"

# 資料庫健康狀態（不回傳 DSN 或密碼）
curl -sS \
  -H "Authorization: Bearer $WAREHOUSE_WORKSPACE_KEY" \
  "$WAREHOUSE_BASE_URL/api/workspaces/v1/database/health"

# 讀取集合
curl -sS \
  -H "Authorization: Bearer $WAREHOUSE_WORKSPACE_KEY" \
  "$WAREHOUSE_BASE_URL/api/workspaces/v1/data/customers?limit=100&offset=0"

# 寫入記錄
curl -sS -X PUT \
  -H "Authorization: Bearer $WAREHOUSE_WORKSPACE_KEY" \
  -H "Content-Type: application/json" \
  --data '{"data":{"name":"Acme","active":true}}' \
  "$WAREHOUSE_BASE_URL/api/workspaces/v1/data/customers/acme?expected_version=0"

# 讀取真實 PostgreSQL 關係表
curl -sS \
  -H "Authorization: Bearer $WAREHOUSE_WORKSPACE_KEY" \
  "$WAREHOUSE_BASE_URL/api/workspaces/v1/database/tables/public/orders/rows"

# 以主鍵與版本寫入關係表
curl -sS -X PUT \
  -H "Authorization: Bearer $WAREHOUSE_WORKSPACE_KEY" \
  -H "Content-Type: application/json" \
  --data '{"data":{"total":125,"currency":"CNY"}}' \
  "$WAREHOUSE_BASE_URL/api/workspaces/v1/database/tables/public/orders/rows/order-1?expected_version=0"
```

穩定工作區端點包括：

- `GET /api/workspaces/v1/info`
- `GET /api/workspaces/v1/usage`
- `GET /api/workspaces/v1/database/schema`
- `GET /api/workspaces/v1/database/health`
- `GET /api/workspaces/v1/database/tables/{schema}/{table}/rows`
- `PUT /api/workspaces/v1/database/tables/{schema}/{table}/rows/{record_key}`
- `GET /api/workspaces/v1/data/{collection}`
- `PUT /api/workspaces/v1/data/{collection}/{record_key}`
- `POST /api/workspaces/v1/sources/upload`
- `GET /api/workspaces/v1/sources`
- `POST /api/workspaces/v1/deployments`
- `POST /api/workspaces/v1/jobs`
- `GET /api/workspaces/v1/deployments[/{deployment_id}]`
- `GET /api/workspaces/v1/deployments/{deployment_id}/events`
- `GET /api/workspaces/v1/deployments/{deployment_id}/logs`
- `POST /api/workspaces/v1/deployments/{deployment_id}/cancel`
- `POST /api/workspaces/v1/deployments/{deployment_id}/activate`
- `PUT /api/workspaces/v1/database/policy`
- `GET /api/workspaces/v1/database/control`
- `POST /api/workspaces/v1/database/reconcile`

`workspace:read` 控制 `info`，`data:read` 控制 schema、健康狀態、集合及關係表讀取，`data:write` 控制記錄與關係表寫入；`deploy:read/write` 控制源碼與部署，`logs:read` 控制脫敏日誌。

資料庫策略可選 `platform_managed`、`external`、`workspace_managed` 或 `none`。前兩者以唯一預設 `database_binding` 驅動 Runtime、Schema、Data API、Migration 與健康檢查，完整 DSN 只加密保存並在 Runtime 啟動前注入，不出現在 API、AI 上下文、審計或日誌。`workspace_managed` 允許 WAK 在受限 Container／Compose 與該工作區命名卷內使用 MySQL、MongoDB、SQLite 或其他引擎並自行管理 Schema；`none` 不注入資料庫。這種自由不包含宿主機 root、Docker socket、host network、host path、特權容器或其他工作區資料。

### 獨立資料庫與 GitHub Pages

`POST /api/database-projects` 可單獨建立資料庫服務，不要求上傳前端、後端或部署 Runtime。它仍使用同一套資產、工作區、`database_binding`、HDD 配額與審計模型，不是另一套旁路資料庫。

AI 秘書原生使用 `dm db service list`、`dm db service create`、`dm db browser show`、`dm db browser configure` 與 `dm db onboarding`。因此它能替使用者申請、盤點、配置並交付 SDK、指南、API 清單、公開 `dbp_` 與 Quickstart。需要服務器端 `wak_` 時，秘書只可復用既有的確認及一次性安全交付；不得在對話內重放明文，PostgreSQL DSN／密碼永不交付給對話或瀏覽器。

若前端位於 GitHub Pages，公司管理員以 `PUT /api/workspaces/{workspace}/database/browser-access` 設定精確 HTTPS Origin 及集合規則。回傳的 `dbp_` 只是公開的簽章專案定位符；瀏覽器先換取短效 `wdb_` Access Token 與可輪換的 `wdr_` Refresh Token，再使用 Browser Data API。`wak_`、公司 Access Token、PostgreSQL DSN 與密碼均不得進入靜態網站。

規則預設拒絕，並可逐集合將 read/write 設為 `deny`、`session` 或 `owner`。`owner` 會由服務端寫入並原子檢查 `owner_id`，避免另一個瀏覽器會話讀取、覆蓋或刪除該記錄。每個專案另有精確 Origin CORS、共享資料庫限流、策略 revision 失效及停用時全會話撤銷。官方零依賴 ES Module 位於 `/api/database-gateway/v1/sdk.js`。

## 7. 公司控制面 API

以下端點使用已登入 Warehouse OS 的公司身份，不使用 `wak_`：

### 文件與客戶端

- `GET /api/digital-assets/guide`：返回 AI 可引用的權威指南內容及下載描述
- `GET /api/digital-assets/guide/download`：正式下載本指南
- `GET /api/digital-assets/cli`：下載按目前網域注入預設地址的 `dam.py`
- `GET /api/digital-assets/hosting-standard`：向 AI 返回託管開發標準、機器契約及下載描述
- `GET /api/digital-assets/hosting-standard/download`：下載《託管應用技術要求 2.3》
- `GET /api/digital-assets/hosting-contract.json`：下載同版本機器可讀契約

### 資產、保管與工作區

- `POST /api/digital-assets`：登記資產
- `POST /api/digital-assets/provision`：一次建立資產、工作區、Data API 與主 Key
- `GET /api/digital-assets/{asset}`：讀取資產、版本、工作區和部署狀態
- `POST /api/digital-assets/{asset}/update`：更新資產主檔
- `POST /api/digital-assets/{asset}/archive`：封存資產
- `POST /api/digital-assets/{asset}/version`：建立資產版本
- `POST /api/digital-assets/{asset}/artifacts`：登記交付物描述
- `POST /api/digital-assets/{asset}/artifacts/upload`：上傳並復算交付物 SHA-256
- `GET /api/digital-assets/{asset}/artifacts/{artifact}/download`：下載交付物
- `POST /api/digital-assets/{asset}/custody`：追加雜湊鏈託管事件
- `POST /api/digital-assets/{asset}/workspace`：建立或觀察既有工作區
- `POST /api/digital-assets/{asset}/workspace-quota`：逐次增加 512 MiB 工作區配額
- `POST /api/digital-assets/{asset}/database`：為資產的工作區建立數據庫綁定
- `POST /api/digital-assets/{asset}/deploy`：建立部署排隊請求
- `POST /api/database-projects`：建立不需要 Runtime 的獨立托管資料庫專案
- `GET /api/database-projects`：安全列出公司全部工作區與獨立數據庫服務

### 工作區管理

- `POST /api/workspaces/{workspace}/storage`：僅在無源碼／code 工件時原地切換代碼 HDD/SSD 綁定
- `POST /api/workspaces/{workspace}/databases`：建立指定工作區的數據庫綁定
- `GET /api/workspaces/{workspace}/database/schema`：以公司身份讀取集合與關係表結構
- `GET /api/workspaces/{workspace}/database/health`：驗證目前預設綁定而不暴露憑證
- `GET /api/workspaces/{workspace}/database/tables/{schema}/{table}/rows`：讀取關係表
- `PUT /api/workspaces/{workspace}/database/tables/{schema}/{table}/rows/{record_key}`：依單一主鍵與版本寫入關係表
- `GET /api/workspaces/{workspace}/data/{collection}`：以公司身份讀取集合
- `PUT /api/workspaces/{workspace}/data/{collection}/{record_key}`：以公司身份寫入記錄
- `POST /api/workspaces/{workspace}/keys`：簽發附屬工作區 Key
- `GET /api/workspaces/{workspace}/keys`：列出 Key 安全元資料
- `POST /api/workspaces/{workspace}/keys/primary/rotate`：原子輪換唯一主 Key
- `POST /api/workspaces/{workspace}/keys/{credential}/revoke`：吊銷單一附屬 Key
- `POST /api/workspaces/{workspace}/runtime`：原地升級 Runtime 並在有源碼時建立部署請求
- `GET|PUT /api/workspaces/{workspace}/database/browser-access`：讀取或配置瀏覽器 Origin、規則、Token TTL 與限流
- `GET /api/workspaces/{workspace}/database/onboarding`：取得 SDK、指南、API、公開專案 Key、Quickstart 與密鑰交付政策

建立客戶自有 PostgreSQL 綁定時，`database_url` 只可在這次公司控制面寫入請求中出現：

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $WAREHOUSE_COMPANY_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"logical_name":"app","provider":"external_postgresql","database_url":"postgresql://bounded_user:secret@db.example.com:5432/app?sslmode=verify-full","is_default":true}' \
  "$WAREHOUSE_BASE_URL/api/workspaces/$WORKSPACE/databases"
```

公司 Access Token 不應嵌入受託管程序。受託管程序只使用限定作用域的 `wak_` Key；`wak_` 也不得反向呼叫公司控制面。

## 8. 保管、部署與外部現實

上傳交付物時建議提交預期 SHA-256。服務端會自行復算，不一致時拒絕寫入。版本、交付物與託管事件共同構成可驗證保管鏈。

永久入口、工作區配置、部署請求和真實運行狀態必須分開解讀：

- `permanent_entry_reserved=true`：入口已保留，不等於應用已部署；
- `deployment.status=queued`：請求已入隊，不等於開始運行；
- `runtime_status=building`：配置或構建進行中，不等於健康；
- `ready + healthy + verified application_url`：才可對外宣稱已上線。

Runtime Controller 只領取指向 verified source 與啟用 profile 的請求。靜態站點由隔離的不可變 release 直接供應；Python／Node 組件在受限 OCI 容器中運行。新版本內部或永久入口健康探測失敗時，原 active revision 保持不變。

## 9. 安全與故障處理

- HTTP 401：Key 格式錯誤、過期、已撤銷或簽章／雜湊驗證失敗。
- HTTP 403：身份缺少公司控制面權限，或工作區 Key 缺少作用域。
- HTTP 404：資產／工作區不屬於目前租戶，或資源不存在；服務端不跨租戶搜尋。
- HTTP 409：工作區歸屬、資料版本、配額 revision 或組件狀態衝突。
- HTTP 422：集合名、記錄鍵、作用域、配額步長或請求資料不符合契約。
- 不要把 `wak_` 放入瀏覽器端 JavaScript；一般服務端整合使用自己的後端代調 Data API，已啟用 Browser Gateway 的靜態網站只使用公開 `dbp_` 與短效 `wdb_`。
- 為不同服務簽發不同標籤、最小作用域和較短有效期的附屬 Key。
- 日誌只記錄 Key hint、credential ID 和審計事件，不記錄完整 Key。
- 永遠不要把聊天中的遮罩 Key、一次性交付描述或 Keychain 當成可部署憑證。

## 10. 2.1 上線前核對清單

1. `dm provision` 經 Passkey 授權後，由 AI Runtime 建立資產、工作區、永久入口、512 MiB 配額、Data API 與主 Key。
2. 從同頁籤一次性安全卡領取並保存 Key，然後安全清除。
3. 從 `/api/digital-assets/cli` 下載最新版 `dam.py`。
4. 執行 `python dam.py info`，確認工作區、Key 類型和作用域。
5. 執行 `python dam.py schema`，確認 Data API 綁定為 `ready`。
6. 新增記錄使用 `expected_version=0`；更新使用上次讀到的版本。
7. 需要擴容時每次只申請 512 MiB，並使用 `expected-revision` 防止併發覆蓋。
8. 只有 `ready + healthy + verified application_url` 才宣稱應用已部署。
9. 不使用任何 2.0 Key、資料庫路徑或客戶端命令；部署只使用 2.1 source/deployment API。
