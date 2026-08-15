# Warehouse OS《託管應用技術要求 2.3》

文件狀態：正式技術契約<br>
契約識別：warehouse.hosting-application.v2.3<br>
適用範圍：數字資產工作區、官方 dm.py、AI 秘書、自動化部署程序

這份標準定義「應用交付什麼」以及「平台保證什麼」。它不是特定框架教學。符合契約的 Python、Node.js、靜態網站、容器或 Compose 專案，應能由同一套 CLI、API 與 AI 秘書流程反覆部署並取得可驗證結果。

2.3 是向後相容的增量契約：平台仍接受 `warehouse.hosting-application.v2.2` manifest；只有需要聲明 lifecycle Job、資料庫身份分離或候選 acceptance 的專案才必須使用 v2.3。舊 manifest 不會因平台升級而失效。

## 01 · 最小交付契約

一個可託管專案必須滿足：

1. 源碼以 ZIP 或 TAR 系列封裝，不能包含絕對路徑、父目錄穿越、裝置文件或逃逸連結。
2. 可由顯式設定或平台偵測得到唯一的啟動入口。
3. HTTP 服務監聽平台注入的 PORT，並監聽 0.0.0.0。
4. 提供不依賴登入的健康檢查路徑；推薦 /healthz。
5. 把源碼視為唯讀，把持久資料寫入 /workspace/data。
6. 依賴、執行時版本、建置與啟動命令必須可重現。
7. 機密只從環境變數或平台 Secret 取得，不得寫入源碼、日誌或回應。
8. 使用平台／外部綁定時從 DATABASE_URL 讀取連線；工作區自管模式可使用自己的安全環境變數與資料引擎。遷移必須可重入、可追蹤並具失敗邊界。
9. 收到終止信號後停止接收新工作、完成短任務並正常退出。

平台只有在「進程運行、健康檢查通過、公開路由驗證成功」三項事實同時成立時，才能把部署標記為 ready。

## 02 · 建議的專案描述文件

專案根目錄可加入 warehouse.hosting.json。缺少描述文件時平台仍可偵測，但正式環境建議顯式宣告。

~~~json
{
  "schema": "warehouse.hosting-application.v2.3",
  "runtime": {
    "type": "api",
    "runtime": "python3.12",
    "entrypoint": "app/main.py",
    "build_command": "pip install --require-hashes -r requirements.txt",
    "start_command": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "port": 8080,
    "health_path": "/healthz"
  },
  "data": {
    "persistent_path": "/workspace/data",
    "database_policy": "platform_managed",
    "runtime_database_url_env": "DATABASE_URL",
    "migration_database_url_env": "APP_MIGRATION_DATABASE_URL"
  },
  "lifecycle": {
    "jobs": [{
      "name": "migrate",
      "command": "alembic upgrade head",
      "database_access": "migration",
      "required_before_activation": true
    }]
  },
  "acceptance": {
    "required_before_activation": true,
    "http": [{
      "name": "health",
      "path": "/healthz",
      "expected_status": 200
    }],
    "database": {"context": {}, "counts": []}
  },
  "deployment": {
    "strategy": "staged",
    "activate_when_healthy": false,
    "retain_previous": true,
    "require_acceptance_before_activation": true
  }
}
~~~

完整 JSON 契約可由以下端點取得：

- /api/digital-assets/hosting-contract.json
- /api/hosting/v2/contract.json

## 03 · 執行時類型

### Python

- 用 requirements.txt、pyproject.toml 或鎖定文件聲明依賴。
- Web/API 服務不得只監聽 127.0.0.1。
- 啟動時不得在源碼目錄生成必要的持久文件。
- 長時間資料遷移不要藏在 Web 進程的 import 階段。

### Node.js

- 提交 package.json 及對應 lockfile。
- 正式執行使用固定的 start 命令，不依賴互動式開發伺服器。
- 前端建置輸出應可重現；API 地址優先採同源相對路徑。

### 靜態網站

- 必須能辨識建置輸出目錄，例如 dist、build 或 public。
- 路由回退、快取策略和資產相對路徑應顯式設定。
- 不得把 Workspace Key 或其他 Secret 編譯進瀏覽器資產。
- 外部靜態網站需要直接存取平台資料時，只能使用已配置精確 Origin 與 deny-by-default 規則的 Browser Data Gateway；`dbp_` 是公開定位符，瀏覽器資料權限來自短效 `wdb_`，不得以 `wak_` 取代。

### Container

- Dockerfile 應固定基礎映像的大版本或 digest。
- 使用非 root 使用者；提供 HEALTHCHECK 或在描述文件中聲明 health_path。
- 寫入只限臨時目錄與 /workspace/data。
- 不假設宿主機路徑、Docker Socket 或特權能力存在。

### Compose

- 公開服務必須以 route_service 指定。
- 有狀態服務應使用平台資料庫或平台配置的持久卷。
- depends_on 不是健康證明；仍需服務級健康檢查。
- Compose 不得自行開放宿主機管理埠。

### 03A · 計算位置與減少雲端 Runtime

平台與 AI 應先判斷「工作必須在哪裡執行」，再建議 Runtime。建議是唯讀設計證據，不得自動改寫源碼、移動 Secret、變更資料庫或啟用新發布。使用者確認後，任何修改仍須建立新的不可變 source、候選部署與健康驗收。

| 工作類型 | 優先計算位置 | 設計邊界 |
|---|---|---|
| 畫面渲染、表單校驗、篩選、排序、非秘密的確定性計算 | 瀏覽器 JavaScript／TypeScript | 不需要雲端 Runtime；仍須量測低階手機的 CPU、記憶體與電量 |
| 純函數 Python 小模組 | 改寫為 JavaScript／TypeScript，或評估 Pyodide／WebAssembly | 只有無 Secret、無特權 I/O、無共享寫入的部分適合移動；採用 Python/WASM 前須量測下載體積與首次啟動時間 |
| Rust、C／C++、Go 的確定性重計算 | 瀏覽器 WebAssembly 或按需 Runtime | 檔案、網路、裝置與執行緒能力必須明確聲明，不因編譯為 WASM 自動取得權限 |
| Java、Kotlin、Scala | 可選 Local Agent 或伺服器 Runtime | JavaScript 與 Java 是不同 Runtime；一般瀏覽器沒有 JVM，不得把 Java 誤稱為可直接在網頁執行 |
| 共用記錄、權限、同步與持久資料 | Platform Database API | 瀏覽器只取得短效、精確 Origin、deny-by-default 的資料權限；不取得資料庫 DSN |
| AI Key、支付、簽名、授權判斷、特權寫入 | Scale-to-zero Function | 保留伺服器信任邊界；空閒時不常駐工作區 Runtime |
| WebSocket、持續 Worker、GPU、長任務 | Dedicated Runtime | 只有可觀測事實證明需要持續進程時才常駐 |

`dm pages design --workspace <workspace>` 與對應 Pages Design API 應回傳 `warehouse.compute-placement-advice.v1`：來源語言與 Manifest 證據、推薦托管模式、每項工作建議位置、安全限制與信心等級。它必須顯式標示 `advisory_only=true`、`automatic_code_rewrite=false` 及 `confirmation_required_before_new_release=true`。

建議的模式只分為三類：`pure_static`、`static_with_on_demand_api`、`on_demand_or_dedicated_runtime_review`。AI 可以提出檔案級修改建議，但不能把 Secret、授權、資料庫憑證或共享狀態移入瀏覽器，也不能用「節省雲端資源」取代安全與相容性驗證。

## 04 · HTTP 與反向代理

應用必須接受 Host、X-Forwarded-Proto 與 X-Forwarded-Prefix。當應用部署在工作區子路徑時：

- HTML、API、圖片與字體使用同源相對 URL，或正確套用 forwarded prefix。
- Service Worker 的 scope 不得超出工作區入口。
- 登入回調和 canonical URL 必須以外部 HTTPS 位址生成。
- 根路徑可以不是健康路徑；平台以聲明的 health_path 判斷健康。

健康端點應快速、無副作用、不洩露配置。建議成功回應：

~~~json
{"status":"ok"}
~~~

## 05 · 文件系統

| 路徑／資源 | 權限與用途 |
|---|---|
| 已解封的源碼 | 唯讀；每個 source_version 不可變 |
| /workspace/data | 工作區持久資料，可寫 |
| /workspace/data/.runtime/python/&lt;digest&gt;/venv | Python 依賴虛擬環境，可寫且按建置摘要隔離 |
| 系統臨時目錄 | 可寫但不保證跨部署保存 |
| DATABASE_URL | 平台資料庫連線，由環境注入 |
| Workspace Key | 控制面認證；不應提供給應用前端 |

資料庫策略有四種：`platform_managed` 由平台建立並注入 PostgreSQL、`external` 注入已驗證外部 PostgreSQL、`workspace_managed` 由工作區 Compose／Secret 自行選擇任何資料引擎、`none` 不使用資料庫。前兩者的 `DATABASE_URL` 由預設 `database_binding` 解析且應用不得覆蓋；後兩者不強制 PostgreSQL，也不啟用平台 PostgreSQL 發布閘門。

應用不能依賴目前工作目錄恰好等於源碼根目錄；路徑應以應用根目錄或平台變數解析。

## 06 · 資料庫與遷移

1. Schema 變更使用具版本的 migration，不以手工 SQL 取代。
2. 遷移在新的應用版本接流量前執行，失敗則不得啟用部署。
3. 擴展與收縮分開進行，避免新舊版本短暫並行時互相破壞。
4. 大表操作應分批，並聲明逾時、鎖定和回復策略。
5. 原生 SQL 必須使用驅動可接受的執行介面；含 JSON 冒號的 SQL 不應被誤解析為綁定參數。
6. 不把密碼、完整連線字串或個資輸出到 migration 日誌。
7. 可用 `POST /api/workspaces/v1/jobs` 執行 Alembic、catalog import 或初始化命令；任務只掛載唯讀源碼與該工作區可寫資料卷，成功不切換正式流量。

### 06A · 資料庫身份分離

- 一般服務只能取得 Runtime DSN；該角色不得是資料庫 owner，也不得具有 `SUPERUSER`、`BYPASSRLS`、`CREATEDB`、`CREATEROLE` 或角色成員資格。
- `database_access: migration` 只允許出現在一次性 lifecycle Job；平台將 owner DSN 注入該 Job 聲明的環境變數，Job 完成後不保留。
- `database_access: runtime` 的一次性 Job 使用與線上服務相同的最小權限角色，適合 RLS 資料導入或相容性檢查。
- 應用不得以 Web 啟動命令取得 migration DSN，也不得把遷移藏在長時間服務的 import 階段。
- 平台備份使用每工作區獨立的 `NOLOGIN + BYPASSRLS` 身份；它只繼承該工作區 owner 權限，Runtime 不得成為其成員。`FORCE ROW LEVEL SECURITY` 不得以關閉 RLS 或只導出 Runtime 可見資料規避。
- logical backup 必須保留 owner、核對校驗和，並在隔離臨時資料庫恢復；所有 FORCE RLS relation 的源庫與恢復庫行數必須逐表一致才可標記 ready。

### 06B · 聲明式發布生命週期

`lifecycle.jobs` 可聲明 migration、seed、catalog import 或索引初始化。每個 Job 必須有唯一名稱、固定命令、資料庫身份、逾時和 `required_before_activation`。正式發布優先使用服務端持久化 Release，而不是由終端逐步串接低階命令：

~~~text
python3 dm.py project doctor --source <SOURCE_VERSION_ID>
python3 dm.py release plan --source <SOURCE_VERSION_ID>
python3 dm.py release run --source <SOURCE_VERSION_ID> \
  --idempotency-key <STABLE_KEY>
python3 dm.py release activate <RELEASE_ID>
~~~

`release run` 依序建立不接流量的候選、執行本次 source 聲明的必要 Job、完成候選驗收，然後停在 `awaiting_activation`。只有使用者顯式執行 `release activate`，平台才切換流量、探測真實公共路由；探測失敗時恢復建立 Release 時記錄的上一版本。需要完整自動化時可在 `release run` 加 `--activate`，這仍屬該命令中的顯式授權。

Release 狀態與事件保存在服務端；終端斷線、CLI 結束或 AI 對話中斷不會丟失進度。重試必須沿用同一 `Idempotency-Key` 或原 `RELEASE_ID`。平台把成功證據綁定到 source version、hosting contract digest、Release 與 Job deployment；其他源碼版本的歷史成功記錄不能滿足本次門禁。

`dm.py job`、`deploy request`、`deploy accept` 與 `deploy activate` 保留為診斷及相容低階接口；日常發布不得再要求使用者手工拼接它們。

### 06D · 平台占用計量

`GET /api/workspaces/v1/usage` 與 `GET /api/workspaces/v1/info` 提供所有工作區一致的占用事實：託管源碼歸檔、全部保留 Runtime release／build／虛擬環境與依賴快取、排除 `.runtime` 後的持久 DATA、託管資料物件、PostgreSQL relation／index／TOAST，以及量測時間與總計。檔案系統量測不跟隨工作負載可建立的符號連結。

### 06C · 公開事實與資料庫事實的雙層驗收

`acceptance.http` 只允許對候選私網地址執行有界 GET，可檢查 HTTP 狀態、JSON 值或 JSON 陣列長度。`acceptance.database.counts` 只允許安全的 relation count 與等值 filter，不接受任意 SQL；查詢固定使用 Runtime 角色並套用 `acceptance.database.context` 聲明的 RLS session setting。

~~~json
{
  "acceptance": {
    "required_before_activation": true,
    "http": [{
      "name": "modules",
      "path": "/api/v1/modules",
      "operator": "length_equals",
      "expected": 8
    }],
    "database": {
      "context": {
        "app.tenant_id": "00000000-0000-4000-8000-000000000001"
      },
      "counts": [{
        "name": "resources",
        "schema": "catalog",
        "relation": "learning_resources",
        "expected": 2
      }]
    }
  }
}
~~~

資料庫總量與公開 API 可見量是不同事實；internal／sensitive 資料不應為了通過公開驗收而降級分類。執行 `python3 dm.py deploy accept <DEPLOYMENT_ID>` 後，只有 source、contract digest、HTTP、必要 Job 與資料庫事實全部相符，`deploy activate` 才能切流。

## 07 · 安全與供應鏈

- 上傳後由服務端重算 SHA-256，客戶端 hash 只作交叉核對。
- 平台在解封前檢查壓縮包安全、大小、成員數與路徑。
- 依賴安裝使用鎖定文件；建議生成 SBOM 並保留來源版本關係。
- Secret 只可由 Secret 資源或環境注入；回應與日誌必須遮罩。
- 應用執行身份採最小權限，不允許特權容器。
- 不把 Workspace Key 放進 Git、壓縮包、瀏覽器 localStorage 或公開日誌。

## 08 · 可觀測性與退出

- 日誌寫 stdout/stderr，使用 UTF-8；推薦每行一個 JSON 事件。
- 每個請求保留平台傳入的 request/correlation id。
- 日誌不得包含 Secret、Authorization header 或完整資料庫連線字串。
- 對 SIGTERM 做優雅退出，不能以無限重試阻塞部署替換。
- Worker 任務應有冪等鍵、逾時及可重試邊界。

## 09 · 平台側保證

Warehouse OS 託管控制面必須：

1. 驗證 Workspace Key 的租戶、工作區與 scope 邊界。
2. 在服務端驗證上傳雜湊及安全解封。
3. 將 source_version 設為不可變並留下操作與部署譜系。
4. 根據來源 digest 重用可信依賴快取，不混用未知版本。
5. 注入 PORT、工作區路徑、已授權 Secret，以及資料庫策略允許時的 DATABASE_URL。
6. 以唯讀源碼和可寫資料卷啟動隔離進程。
7. 僅把 migration owner 身份注入聲明式一次性 Job；一般服務與 Runtime Job 使用最小權限角色。
8. 在候選私網地址執行 manifest 聲明的 HTTP 驗收，並以 Runtime 角色核對 RLS 範圍內資料庫事實。
9. 將驗收證據綁定到 source version、contract digest 和 deployment，拒絕沿用其他版本的成功結果。
10. 只有通過必要 Job、健康、驗收與資料庫門檻才啟用；失敗時保留前一個健康版本。
11. 回傳階段、證據、錯誤代碼和經遮罩的日誌，不用籠統的成功訊息取代事實。
12. 健康檢查必須包含實際寫入探針；僅存在配置或資料列不等於儲存可用。
13. 向使用者與 AI 提供有來源證據的計算位置建議；建議本身永不改寫程式、資料或活動發布。
14. 將候選、必要 Job、驗收、待激活、公共路由驗證及回滾保存為可續跑 Release；任何客戶端斷線不得使流程失憶。
15. 在建立候選前拒絕互相矛盾的交付聲明，例如純靜態交付同時要求資料庫 Runtime 環境、必要資料庫 Job 或 `/api/` 候選驗收。

## 10 · 上線前檢查表

- [ ] 壓縮包可安全解封，服務端 SHA-256 與本地一致
- [ ] 描述文件或偵測結果只有一個明確入口
- [ ] 依賴有 lockfile，建置不需互動
- [ ] 服務監聽 0.0.0.0:$PORT
- [ ] health_path 在未登入狀態返回 2xx
- [ ] 持久寫入只進入 /workspace/data 或平台資料庫
- [ ] Secret 未進入源碼、前端資產與日誌
- [ ] 已區分 JavaScript、Java、Python/WASM 與伺服器信任邊界
- [ ] 瀏覽器計算建議已量測下載體積、首次啟動時間及手機記憶體
- [ ] 計算位置建議只讀；任何採納結果均建立新 source、候選與回滾點
- [ ] migration 可重入，失敗不接流量
- [ ] Runtime 與 migration 使用不同資料庫身份，Web 服務拿不到 owner DSN
- [ ] 必要 lifecycle Job 的成功證據屬於本次 source 與 contract digest
- [ ] `project doctor` 與 `release plan` 沒有類型、權限或資料庫門禁 blocker
- [ ] Release 使用穩定 Idempotency-Key，斷線後可按原 ID 繼續
- [ ] acceptance 同時區分公開可見量和 RLS 範圍內資料庫總量
- [ ] 子路徑、靜態資產和登入回調已測試
- [ ] SIGTERM 可正常退出
- [ ] 公開入口回應包含正確的部署證據
- [ ] 回滾到上一健康版本已演練

## 11 · 標準下載與自動化

人類可直接下載本文件；程式可以讀取同版本 JSON 契約：

- GET /api/digital-assets/hosting-standard/download
- GET /api/digital-assets/hosting-contract.json
- GET /api/hosting/v2/developer-standard.md
- GET /api/hosting/v2/contract.json
- GET /api/hosting/v2/requirements

官方 CLI：

~~~text
python3 dm.py hosting requirements
python3 dm.py project doctor --source <SOURCE_VERSION_ID>
python3 dm.py release run --source <SOURCE_VERSION_ID> \
  --idempotency-key <STABLE_KEY>
~~~

AI 秘書可使用「dm hosting requirements」能力，把 Markdown 與 JSON 下載卡直接交給使用者。文件與契約使用同一版本號；任何破壞相容性的要求都必須提升契約版本。
