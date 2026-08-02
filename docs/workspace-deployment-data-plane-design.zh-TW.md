# Warehouse OS 2.1 工作區源碼與部署資料面設計

狀態：已實作 v1（2026-08-02）<br>
設計日期：2026-08-02<br>
適用範圍：數字資產工作區、`wak_` Key、AI 秘書、超級終端、外部自動化客戶端

## 1. 現況結論

目前 2.1 已完成的是真實托管控制面與資料面基礎：

- 資產、工作區與永久入口持久化；
- 主 Key／附屬 Key 與公司隔離；
- HDD/SSD code binding、HDD data binding 與 512 MiB 邏輯配額；
- HDD PostgreSQL 工作區資料庫與穩定 JSON Data API；
- source artifact、asset version、component、deployment 與事件資料模型。

但部署閉環尚未完成：

- `wak_` Key 宣告包含 `deploy:read`、`deploy:write`，卻沒有可用的工作區 source/deploy API；
- `dam.py 2.1` 只有 `info/schema/list/put`；
- 公司控制面 `/api/digital-assets/{asset}/artifacts/upload` 與 `/deploy` 只接受公司 Access Token；
- `create_deployment()` 只建立 `provider_key=runtime_queue` 的 queued 記錄；
- 沒有 Runtime worker 領取、建置、啟動、健康探測及切流；
- `runtime_hosting_snapshot()` 正確標示 `container_runtime=false`、`runtime_provider_state=worker_pending`。

因此目前是「可托管資產與資料，但不能由工作區 Key 完成應用部署」，不是完整的應用托管。

## 2. 設計原則

1. **Key 的 scope 必須對應真實 API**：`deploy:read/write` 不能只是裝飾。
2. **原子能力，不寫死流程**：上傳、定版、請求部署、觀察、取消、回滾各自是原子能力；AI 根據世界狀態決定如何組合。
3. **同一領域服務、人機同源**：公司控制面、工作區 Key、AI 秘書與 CLI 共用一套 domain service，不複製業務邏輯。
4. **外部事實只能由探測產生**：AI、使用者或資料庫 mutation 都不能自行把部署標成 ready。
5. **源碼不可變、部署可追溯**：每次部署必須指向已驗證 SHA-256 的 source artifact 與 asset version。
6. **DATA/DB 永遠在 HDD**：code 依工作區 binding 使用 HDD 或 SSD；建置暫存不計作持久資料。
7. **權限與安全邊界固定，業務判斷交給 AI**：租戶隔離、配額、路徑越界、雜湊、Runtime 沙箱是強制不變式；部署策略與下一步由 AI 判斷。

## 3. 統一身份模型

把現有只接受 `ActorContext` 的部署服務重構為 `WorkspaceOperationPrincipal`：

```text
principal
├── tenant_id
├── workspace_id
├── asset_id
├── identity_kind: company_user | workspace_key | auto_runtime | runtime_worker
├── identity_id
├── scopes / permissions
└── audit_origin
```

- 公司使用者：由 Access Token 解析，可跨目前公司的多個工作區操作；高風險操作仍走 Passkey → Keychain → AI Runtime。
- 工作區 Key：只綁定一個 tenant/workspace，不接受客戶提供 asset/workspace 路徑來擴張範圍。
- Auto Runtime：在目前公司邊界內觀察全部能力，執行仍通過同一 typed adapter。
- Runtime worker：只持有一次 deployment lease，不能任意讀其他工作區。

既有 scope 不改名，直接履行已簽發契約：

| Scope | 真實能力 |
|---|---|
| `workspace:read` | 工作區、組件、儲存與非機密狀態 |
| `data:read/write` | 工作區 Data API |
| `deploy:read` | source/version、deployment、events、logs、health |
| `deploy:write` | source upload/finalize、request/cancel/rollback |
| `logs:read` | Runtime 與建置日誌的安全投影 |

主 Key 擁有全部 scope；附屬 Key 可只簽發部署或只讀權限。自動化及 CI 應使用附屬 Key，不使用主 Key。

## 4. Workspace Deployment API v1

全部路由從 `WorkspaceCredential` 取得 workspace，不接受任意 workspace id：

### 4.1 源碼

```text
POST /api/workspaces/v1/source-uploads
PUT  /api/workspaces/v1/source-uploads/{upload_id}/content
POST /api/workspaces/v1/source-uploads/{upload_id}/finalize
GET  /api/workspaces/v1/sources
GET  /api/workspaces/v1/sources/{version_id}
```

建立 upload session 時返回：最大可寫位元組、目前 code medium、有效期與 upload id。內容串流必須攜帶 `Content-SHA256`；finalize 才能：

1. 復算 SHA-256；
2. 驗證 archive 沒有絕對路徑、`..`、symlink/hardlink 逃逸或解壓炸彈；
3. 依工作區 code binding 寫入 content-addressed object store；
4. 同一交易建立 verified artifact、asset version 與 custody event；
5. 返回可被部署引用的 `source_version_id`。

小型客戶端可額外提供單次 multipart convenience endpoint，但其內部仍走相同 upload/finalize service。

### 4.2 部署

```text
POST /api/workspaces/v1/deployments
GET  /api/workspaces/v1/deployments
GET  /api/workspaces/v1/deployments/{deployment_id}
GET  /api/workspaces/v1/deployments/{deployment_id}/events
GET  /api/workspaces/v1/deployments/{deployment_id}/logs
POST /api/workspaces/v1/deployments/{deployment_id}/cancel
POST /api/workspaces/v1/deployments/{deployment_id}/rollback
```

部署請求只接受已驗證的 source version、既有 component 及可攜 runtime intent。`Idempotency-Key` 與 `(workspace, component, source digest, intent digest)` 防止 AI 重試時重複建置。

請求成功只代表 `queued`，絕不返回已部署。讀取接口返回：

- deployment revision 與 source digest；
- worker lease／build／runtime／health 的可觀察狀態；
- append-only events；
- 經脫敏、限量與分頁的 logs；
- `verified_application_url` 或明確的 `not_verified`。

## 5. Runtime Controller

新增獨立服務 `warehouse-runtime-controller`，與 Warehouse API 分離。它使用受限資料庫角色並以 `FOR UPDATE SKIP LOCKED` 領取 queued deployment，寫入有期限的 lease。

每個 deployment 執行以下可觀察階段，但階段不是 AI 的硬編碼工作流，只是 Runtime provider 的技術狀態：

```text
claimed → source_verified → build_started → image_built
        → instance_started → health_verified → route_activated
```

任何一步失敗都追加事件並留下可重試證據；上一個 healthy revision 保持服務，直到新 revision 完成 health verification 才原子切流。

Runtime profile 不寫死在 Python `if/else`，存於資料庫並由 provider adapter 執行：

```text
platform.runtime_profiles
├── profile_key
├── detector_contract       # manifest / file evidence
├── build_provider
├── default_build/start/health contract
├── allowed_runtime/image families
├── resource limits
├── network policy
└── enabled / version
```

AI 可以根據 `pyproject.toml`、`requirements.txt`、`package.json`、Dockerfile 或使用者描述提出 profile/component intent；安全 validator 只核對資源上限、允許的 provider 及不可突破的不變式。

## 6. 執行隔離與儲存

- 使用 rootless BuildKit/Podman 或等價 OCI builder；不得在 Warehouse API 容器內直接 `pip install` 或執行使用者程式。
- 解壓與 build 在一次性沙箱；依賴下載有時間、空間及網路策略。
- Runtime 使用獨立 UID、cgroup CPU/RAM/PID 限額、read-only root filesystem。
- code layer 來自不可變 image/source digest。
- DATA 與持久化 volume 只掛載 HDD 工作區目錄；資料庫仍通過 Data API，不向應用暴露管理 DSN。
- Runtime 需要平台 API 時注入短效、可輪換的 workload credential，不能把主 `wak_` 寫入 image、argv 或日誌。
- 512 MiB 是 code + data + database + runtime persistence 的邏輯總上限，不預佔空間；build cache 使用平台暫存配額另行治理。

## 7. 永久入口與外部事實

永久入口保持：

```text
https://bonfirework.org/assets/{tenant_slug}/{workspace_key}/
```

- 未部署：顯示工作區狀態頁；
- 部署中：顯示可觀察進度，不假裝網站可用；
- healthy：由 Runtime Gateway 將同一入口反代至 active revision；
- 新版失敗：保持上一個 healthy revision，不中斷入口；
- 回滾：切換到既有已驗證 image digest，不重新解釋或重建源碼。

只有 Runtime controller 同時確認 container active、內部健康探測通過、公開路由探測通過後，才可寫入：

```text
deployment.status = ready
deployment.health = healthy
workspace.runtime_status = ready
active_revision = deployment.revision
```

`public_url` 不能由一般 mutation 或部署請求直接變成外部事實。

## 8. AI 能力與 CLI

新增共享能力基因：

```text
workspace_source_upload
workspace_source_list
workspace_deploy_request
workspace_deploy_observe
workspace_deploy_logs
workspace_deploy_cancel
workspace_deploy_rollback
```

每個能力只描述 typed input、效果、風險、證據與可用 affordance。AI 可依觀察結果自由組合，不規定「一定先問哪個問題」或固定部署流程。

`dam.py` 增加：

```text
dam.py source push ./app.zip --version v1
dam.py source list
dam.py storage probe
dam.py runtime set --type auto --source <version>
dam.py runtime set --type api --runtime python3.12 --source <version> --deploy
dam.py deploy request --source <version> --component api
dam.py deploy status [deployment]
dam.py deploy logs <deployment>
dam.py deploy activate <healthy-deployment>
```

Runtime 類型是語義介面，執行 profile、映像、探測契約與資源限制仍由資料庫定義。`auto` 讀取 verified source 證據後選擇 profile；使用者或 AI 可明確覆寫，不存在固定的業務流程。

## 9. 前端

數字資產工作區抽屜顯示：

- source versions 與最新 digest；
- component/runtime profile；
- build/deployment/health 事件時間線；
- active 與 previous healthy revision；
- code SSD/HDD、DATA HDD、DB HDD 與共同配額；
- 「上傳源碼」「部署此版本」「查看日誌」「回滾」按鈕。

手動按鈕與 AI 使用同一 capability catalogue。公司使用者的高風險操作卡只返回授權 Keychain；AI Runtime 領取後呼叫同一 domain service。工作區 Key 客戶端則由 scope 直接授權，不再要求公司 Access Token。

## 10. 審計與機密

- Authorization header、`wak_` 明文、workload credential、DSN 不得進 request snapshot、command trace、日誌或 RTF/聊天記憶。
- 審計只保存 credential id/hint、workspace、source digest、deployment id、scope、origin 與結果。
- upload/deploy/rollback 都要有 idempotency key、request digest 與 append-only event。
- 完整主 Key 一旦出現在文件、終端 transcript 或聊天中，視為已洩漏，必須輪換。

## 11. 舊版經驗的取捨

可保留：

- Key 可直接操作自己的工作區；
- upload 與 deploy 分離；
- 真實 system/runtime/port/HTTP 健康探測；
- 低權限執行、日誌、restart、doctor 與回滾能力；
- 特權操作只允許由狹窄 controller 執行。

不直接移植：

- 固定 `main.py`/ASGI；
- 固定 18000–19999 端口分配；
- 每工作區 root systemd 腳本直接安裝任意依賴；
- 把長效主 Key 寫入 `runtime.env`；
- 以目錄同步結果代替 source digest、image digest 與 deployment revision；
- 刪除式更新及無健康驗證切流。

## 12. 實作順序

### A. 關閉契約缺口

1. 抽出共享 principal/domain service；
2. 建立 workspace source upload/finalize API；
3. 建立 workspace deployment read/write API；
4. 擴充 `dam.py` 與 OpenAPI；
5. 加入租戶、scope、配額、雜湊、archive traversal、冪等與密鑰脫敏測試。

狀態：已完成。Key 可真實建立 source version、queued deployment、事件與日誌投影。

### B. 真實 Runtime

1. 建立 controller、lease、build job 與 runtime instance；
2. 接 rootless build provider；
3. 實作健康探測與事件；
4. 接 Runtime Gateway 與原子切流；
5. 建立失敗保持舊版、取消與回滾。

狀態：已完成 v1。Runtime Controller、lease、安全 materialize、靜態 gateway、Python／Node OCI provider、健康探測、舊版保留與 verified revision 切換已接通，`container_runtime=true`。

### C. AI 與前端閉環

1. 註冊共享能力基因及手動操作；
2. 將 source/deployment world observation 注入多層上下文；
3. 前端顯示進度、日誌與 active revision；
4. 用真實 `wak_`、公司 AI 與手動 UI 跑同一端到端測試；
5. 驗證永久入口、冷啟動、失敗保持舊版與回滾。

狀態：CLI、Runtime 世界快照與現有工作區控制台投影已完成；前端目前沿用同一資產抽屜顯示永久入口、源碼與部署狀態，後續可再加入二進制拖放上傳的專用面板。

## 13. 驗收標準

對一個只有工作區與 Key 的新資產，外部客戶端必須能：

1. `info` 取得工作區與 scope；
2. 上傳 zip 並得到服務端復算 digest 及 source version；
3. 請求部署並得到 queued receipt；
4. 觀察完整事件與脫敏日誌；
5. 在 Runtime health 通過後從永久入口訪問應用；
6. 新版啟動失敗時舊版仍可訪問；
7. 使用已驗證 revision 回滾；
8. 全流程只看到本公司、本工作區資料；
9. DATA/DB 保持 HDD，配額與實際用量一致；
10. 審計與聊天中不存在任何完整 Key。
