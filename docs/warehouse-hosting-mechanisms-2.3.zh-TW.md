# Warehouse OS 2.3《託管機制與 Auto Runtime 連接指南》

> 適用於 Warehouse OS 2.1 數字資產工作區；託管控制面採用 2.3 的機器契約版本。
>
> 這份文件是給 AI 秘書、終端 AI、前端整合與應用開發者的共同契約。
> 它說明「程式碼放在哪裡、誰提供計算、狀態如何同步、哪個接口可以連接」；
> 它不是另一套命令流程，也不會取代資料資產託管指南或 2.3 Hosting Contract。

## 1. 先給使用者的選擇

每個 workspace 只有一個託管選擇，但可以隨時由使用者或 AI 秘書提出變更：

| 模式 | 程式碼與狀態 | 計算在哪裡 | Warehouse OS 做什麼 |
| --- | --- | --- | --- |
| `cloud` | 原始碼、版本、Data API 與部署證據在平台 | `warehouse`、`vultr` 或 `mac_mini` 節點 | 建置、啟動、健康檢查、流量切換與用量採集 |
| `terminal` | 原始碼、版本與 Data API 在平台；本機留有受使用者控制的工作目錄 | `user_terminal`（使用者電腦） | 產生最小操作 Manifest、通知終端/AI、驗證完成回執 |

`terminal` 不會偷偷變成雲端，也不會建立常駐 Warehouse Runtime；`cloud` 也不會
把計算推到瀏覽器。若終端離線、資源不足或使用者沒有批准，狀態必須停在
`awaiting_terminal`，由 Auto Runtime 說明原因或詢問使用者。`cloud_fallback=ask`
只代表可以詢問，絕不代表靜默切換。

### Compute node 與 Runtime profile

- `warehouse`：Warehouse Runtime Controller 管理的 Docker 容器；只採集自己的
  active deployment，避免重複計費。
- `vultr`：Vultr worker 管理的節點；worker 透過同一個 compute-usage API 回報，
  Warehouse 不猜測遠端計量。
- `mac_mini`：客戶或平台管理的 Mac mini worker；使用同一份 workspace、Data API
  與部署證據契約。
- `user_terminal`：使用者的終端或終端 AI；平台只簽發來源 hash、Runtime 意圖與
  Data API 連接資料，不給 DSN、主機路徑或公司控制面憑證。

Runtime profile 是「應用需要什麼」的描述，不是固定工作流。可使用
`static`、`web`、`api`、`worker`、`agent`、`job`、`container`、`compose`；
`auto` 讓 AI 依來源觀察與健康證據選擇。profile 只能描述 runtime、entrypoint、
build/start command、health path、port、Compose service 等意圖；秘密必須經由
fabric endpoint 直接寫入，不能放進對話 desired state。

### 可組合的執行機制（使用者可以自己選）

`cloud`/`terminal` 是控制面的兩種模式；下面的執行機制是這兩種模式可以承載的
計算面。AI 秘書必須先詢問或讀取使用者的選擇，再用 Auto Runtime 的 live evidence
決定是否可用，不得把機制當成第三套命令樹。

| 執行機制 | 建議模式 / profile | 計算位置 | 適合情境 | Warehouse 端資源與費用 |
| --- | --- | --- | --- | --- |
| 靜態 / 瀏覽器（MKS/MSU 類） | `terminal + static/web` | 使用者瀏覽器的 JS/WASM/Worker | 前端、儀表板、互動工具 | 只提供版本、靜態檔案與 Data API，幾乎不佔 Runtime 記憶體 |
| 使用者終端 Runtime | `terminal + web/api/worker/agent/job` | 使用者電腦、手機或終端 AI（需批准的 sandbox） | 本地 CPU/GPU、私有檔案、離線或個人工作流 | 不建立常駐雲端 Runtime；平台保存同步資料、通知與完成證據 |
| Warehouse Cloud Runtime | `cloud + api/worker/agent/job/container/compose` | Warehouse Runtime Controller 管理的節點 | 穩定網址、共享後端、排程、長任務 | 按實際 CPU/記憶體/網路/GPU 用量計入雲計算帳本 |
| Vultr / Mac mini Cloud Runtime | `cloud +` 上述 server profiles | 選定的 Vultr 或 Mac mini worker | 專用記憶體、GPU 或既有節點 | 由對應 worker 回報用量；不把遠端資源誤算成 Warehouse 本機用量 |
| Hybrid 分工 | `terminal + static/web` 加 `cloud + api/worker` | 前端與可平行計算在使用者端，必要 API/資料服務在雲端 | 大量使用者本地計算、同時需要共享狀態或穩定入口 | 只有雲端部分產生雲計算用量；兩邊共用 workspace Data API 與版本證據 |

選擇機制時，AI 應向使用者說明「計算在哪裡、是否需要批准、離線時會怎樣、會不會
產生雲計算費」。Hybrid 不是靜默 fallback：它必須在 `desired_state` 中明確表達，並
由同一個 `session_id` 記錄兩個執行面的證據。

其中 `terminal + static/web/worker` 就是 MKS/MSU 類的瀏覽器或使用者裝置計算：
HTML/CSS/JS/WASM/Worker 由 Git/物件儲存下載到瀏覽器，身份和共享狀態只經 Workspace
Data API；Warehouse 不為每個頁面啟動一個 Python/Node 容器。需要常駐後端、私有網路、
大型資料庫或長時間任務時，AI 才應建議 `cloud + api/worker/container/compose`，並把
計算用量與費用說清楚。

## 2. 三個不變量

1. **使用者選擇優先。** `desired_state.hosting.mode` 與 `compute_node` 是顯式
   意圖；系統不依照記憶或模型猜測而改變模式。
2. **外部世界要有證據。** queued、provisioned 或一筆資料庫寫入，都不能宣稱
   應用已上線。Cloud 要有 `ready + healthy + verified URL`；terminal 要有
   terminal completion 回執，並保留 server `runtime_status=provisioned`。
3. **每個租戶都在自己的 RLS 會話。** workspace key (`wak_...`) 只包含該租戶/
   workspace 與 scopes；不暴露 DSN、token hash、主機路徑、Docker socket 或其他
   租戶資料。

## 3. Auto Runtime 是唯一的 AI 行動邊界

Web 秘書、Super Terminal、內嵌助手、Runtime API client 與終端 AI 都遵循同一條
呼叫鏈；surface 只影響呈現，不可選 provider、繞過權限或直接選資料庫：

```text
使用者目標 / desired_state
          |
          v
POST /api/agent/run/stream
          |
          v
Auto Runtime：理解 -> 觀察 -> 選 domain/family/gene -> 計畫
          |
          +--> hosting_world / authority / source / deployment evidence
          |
          v
同一份 command catalogue（legacy_catalog + verified/native adapter）
          |
          v
execute_runtime_tool_call (origin=auto_runtime)
          |
          v
FastAPI domain adapter -> PostgreSQL RLS / Runtime Controller / Data API
          |
          v
讀回證據 -> reflection -> final / requires_user_input / incomplete
```

### AI 可以選的能力層

| 層 | 典型命令 gene | 何時使用 |
| --- | --- | --- |
| 原生託管能力 | `digital_market_hosting_guide`、`digital_market_hosting_requirements`、`digital_market_hosting_start`、`digital_market_hosting_continue`、`digital_market_hosting_status`、`digital_market_hosting_events` | 讀取本指南/技術要求，建立或繼續可恢復會話、觀察部署和精確診斷 |
| 雙模式控制面 | hosting mode/notification/compute-usage 端點 | 讀取或更新使用者選擇、通知與用量；不可偽造完成 |
| 終端交付 | terminal action manifest / complete | terminal 模式取得最小來源包、回報使用者批准的執行結果 |
| Data API / 語義資料 | `generic_data_resources`、`generic_data_schema`、`generic_data_observe`、`generic_data_query`、`generic_data_mutate` | 查詢 workspace、版本、部署、配置與可安全修改的資料 |
| 物理資料庫 Runtime | `database_catalog`、`database_schema`、`database_query`、`database_execute` | AI 判斷需要真實 schema/row 值時；仍由 `ai.database`、RLS、交易與審計約束 |
| 能力缺口 | `data gaps` / capability-gap 回執 | 找不到真實 adapter 時如實回報並留下可提升的缺口，不把失敗寫成成功 |

命令的 `tool_name`、參數 schema、`api_method/api_path`、`writes`、`risk`、
`confirmation_policy` 與 permission 只從 `app/terminal/legacy_catalog.py` 和
verified adapter registry 讀取。AI 的 schema 是發現資料，不是授權；每次執行仍會
重新載入目前租戶權限、RLS、確認卡片、冪等鍵與審計。平台 scope 的 command 需要
L11 governance，不會出現在租戶 AI 的可執行集合。

目前託管相關 command 的權限語義是：`digital_market_hosting_guide` 和
`digital_market_hosting_requirements` 使用 `ai.use`（只讀）；`start`/`continue`
使用 `asset_mgmt.manage`（受控寫入），`status`/`events` 使用 `asset_mgmt.read`（只讀）。
終端的 `/api/cli/exec` 仍受登入者的 `terminal.use` 與細粒度 `cli.*` 能力約束；
`database_*` gene 另受 `ai.database`。實際 `available/authorized/confirmation_required`
每次以 live catalogue response 為準，文件不會擴大權限。

對寫入、Key、部署、外部 provider 等高風險效果：AI 必須等待已註冊的確認政策，或
返回 `requires_user_input`。Passkey/Action Keychain 只是一次性授權信號，不是另一個
執行器；AI 收到信號後必須重新觀察，再由同一個 Runtime executor 執行並核驗。

### 指令集和能力發現接口

這些是現有的真實入口；它們只提供目錄、能力狀態或同一個執行邊界，不會另起一套
託管 planner：

```http
GET  /api/runtime/world                         # 租戶隔離的 live world snapshot
GET  /api/runtime/skills                        # 人可搜尋的 Skills/歷史能力
GET  /api/business/actions                      # 表單、終端、AI 共用 action contract
GET  /api/cli/commands                          # 當前帳號的命令/權限/adapter 狀態
GET  /api/cli/migration-status                  # command adapter 遷移狀態
GET  /api/ai/tools                              # 模型工具 schema + 非秘密 capability state
POST /api/cli/exec                              # 人類終端，共用 command executor
POST /api/business/actions/{tool_name}/execute  # schema 表單，共用 command executor
POST /api/ai/tools/{tool_name}/execute          # 外部 AI 工具，共用 command executor
POST /api/agent/run/stream                      # AI 秘書/Auto Runtime 唯一 goal ingress
```

`/api/runtime/skills` 只是 discovery，不等於可執行；`/api/ai/tools` 的 schema 也不
授權。Auto Runtime 內部以 `ai_capability_atlas → ai_capability_candidates →
ai_capability_genes` 做分層展開，最後才呼叫 `execute_runtime_tool_call`。人類終端和
外部 AI 則分別用 `execute_cli_line`/`execute_tool_call`，但都落入相同的
`_execute_entry`、native/verified adapter、RLS、確認和審計邊界。

## 4. 智能託管 API 連接

### 4.1 先下載契約與指南

```http
GET /api/hosting/v2/manifest
GET /api/hosting/v2/auto-runtime-guide.md
GET /api/hosting/v2/auto-runtime-guide
GET /api/hosting/v2/dm.py
GET /api/hosting/v2/dm-guide.md
GET /api/hosting/v2/developer-standard.md
GET /api/hosting/v2/contract.json
```

`manifest.downloads` 會包含這份文件。AI 秘書應在使用者要求「說明託管方式、
如何連接終端、如何接 API」時，把 `auto-runtime-guide.md` 的下載地址原樣提供，
而不是生成未驗證的主機路徑或 URL。

不含 `.md` 的 `auto-runtime-guide` 是給 Auto Runtime/AI 秘書的完整 JSON 包，包含
`content`、版本、schema 和同源下載卡；共享 executor 使用它避免把 Markdown
`FileResponse` 截斷。直接文件下載仍使用 `.md` 路由。

### 4.2 認證和會話

互動式 AI 秘書使用 account session；外部終端 AI 使用 workspace key：

```http
Authorization: Bearer wak_<workspace-key>
```

建議 scopes：`workspace:read`、`deploy:read`、`deploy:write`、`logs:read`；只讀
助手不要索取 `deploy:write`。公司控制面的 CLI/Runtime key (`wsk_...`) 只供
`/api/agent/run/stream`、`/api/cli/exec` 等統一 Runtime 邊界，不要交給使用者程式。

### 4.3 會話與來源

```http
POST /api/hosting/v2/sessions
POST /api/hosting/v2/sessions/{session_id}/messages
POST /api/hosting/v2/sessions/{session_id}/messages/stream
GET  /api/hosting/v2/sessions/{session_id}?refresh=true
GET  /api/hosting/v2/sessions/{session_id}/events
POST /api/hosting/v2/sessions/{session_id}/sources
POST /api/hosting/v2/sessions/{session_id}/cancel
```

`execute=false` 先取得觀察與計畫；檢查 desired state、storage、Runtime profile、
hosting mode 後，再在同一 `session_id` 以 `execute=true` 繼續。不要因為缺源碼、
缺 scope 或 provider blocked 而新建第二個 workspace；同一會話保存證據、錯誤 stage
與 next step。

### 4.4 雙模式、通知和用量

```http
GET  /api/hosting/v2/hosting?workspace_ref=<workspace>
GET  /api/hosting/v2/notifications?workspace_ref=<workspace>&status=pending
POST /api/hosting/v2/notifications/{notification_id}/ack?workspace_ref=<workspace>
GET  /api/hosting/v2/compute-usage?workspace_ref=<workspace>
```

控制面等價入口（公司 session）是：

```http
GET|PUT /api/workspaces/{workspace}/hosting
GET     /api/workspaces/{workspace}/hosting/notifications
POST    /api/workspaces/{workspace}/hosting/notifications/{notification}/ack
GET     /api/workspaces/{workspace}/compute-usage
```

Cloud worker 以 interval delta 回報 CPU seconds、memory bytes、network bytes、GPU
seconds 和 `metering_source`；`warehouse` 由 Runtime Controller 採樣，Vultr/Mac mini
由各自 worker 回報。第一筆採樣只是 baseline，不能追補重啟期間的用量。此 ledger
是證據，不等於目前已開立費用。

### 4.5 Terminal 交付和資料同步

```http
GET  /api/hosting/v2/terminal-actions/{deployment_id}?workspace_ref=<workspace>
POST /api/hosting/v2/terminal-actions/{deployment_id}/complete?workspace_ref=<workspace>
```

Manifest 只提供 source version/hash、受限 source download route、Runtime 意圖、
Data API 與 completion route。終端應先下載、驗 hash、安全解包，再由使用者批准的
sandbox 執行；`dm.py hosting prepare` 本身不執行不受信任命令。完成回執應包含
`status`、可選 `url`/`result`、`execution_id` 和錯誤摘要，不能把 DSN、公司 token
或主機路徑放入 payload。Cloud/terminal 兩種模式的程式資料都用 workspace Data API
同步，避免把本機資料庫當成平台真實狀態。

## 5. 應用程式設計和接口連線準則

### 應用程式（被託管的專案）

1. 啟動時由環境或 Data API 取得配置，不把 `wak_`、DSN、secret 寫進 repository。
2. 程式提供可重複的 health endpoint（通常 `/health`）；ready 只由平台健康檢查
   和已驗證 URL 給出。
3. 絕對路徑、Docker socket、host networking、privileged container、其他租戶資料
   都不屬於應用契約。
4. 寫入 Data API 使用 `expected_version`/冪等鍵，讀回版本和結果；遇到 409 應由
   AI 秘書重新觀察，不要盲目重試。
5. Terminal 應用把計算留在使用者終端；需要共享狀態時只透過 workspace Data API，
   不把平台資料庫連線字串下發到本機。

### 前端/AI client

1. 把 API base URL 配置成環境值；不要拼接未經 manifest 宣告的 route。
2. 以 `run_id`、`conversation_id`、`session_id` 和 `idempotency_key` 關聯所有重試。
3. 只把 allowlisted activity（phase/status/tool name）顯示給使用者；不展示 raw
   prompt、reasoning、token、DSN、secret 或未驗證地址。
4. 收到 `awaiting_terminal`、`blocked`、`requires_user_input` 時展示下一步，不能
   把 queued/provisioned 翻譯成「已上線」。
5. 任何完成頁都提供 manifest、通知、用量和事件查詢入口，讓使用者能回看證據。

### 最小終端實作流程

```text
GET manifest
  -> GET terminal-action manifest
  -> verify hosting_mode/target/source_sha256
  -> download source and safe-unpack
  -> user-approved sandbox execution
  -> sync data through workspace Data API
  -> POST terminal-action complete
  -> poll notification/events and show verified result
```

## 6. 不可以做的事

- 不要讓模型或前端傳 `tenant_id`、DSN、provider secret、host path、Docker socket、
  arbitrary URL 或資料庫 selector。
- 不要把 `/api/ai/tools` 的 schema 當成授權，也不要直接呼叫 domain service/SQL，
  必須經 Auto Runtime 或已註冊的 authenticated adapter。
- 不要因為一筆寫入、`queued`、`provisioned`、使用者提供 URL 或本機程序啟動就聲稱
  外部網站 ready。
- 不要在 terminal 模式自動 fallback 到 cloud，不要在 `hosting prepare` 自動執行
  source archive 內的命令。
- 不要將命令結果中的明文 workspace key、credential、token hash、raw SQL 或模型
  reasoning 寫入 chat、NDJSON activity、conversation history 或可公開下載文件。

## 7. 版本和真實來源

- 雙模式資料模型與通知/用量：`digital_asset.workspaces`、`hosting_notifications`、
  `compute_usage_events` 及 `app/services/hosting_modes.py`。
- Auto Runtime 路由：`app/services/auto_runtime.py`；共用指令目錄：
  `app/terminal/legacy_catalog.py`、`app/terminal/catalog.py`；執行邊界：
  `app/terminal/executor.py`。
- 智能託管 API：`app/api/intelligent_hosting.py`、`app/services/intelligent_hosting.py`。
- 應用技術限制與機器契約：`workspace-hosting-developer-standard-2.3.zh-TW.md`、
  `workspace-hosting-contract-2.3.json`。

任何文件、CLI 或 AI 回答與上述 live manifest/adapter 狀態不一致時，以 API 回傳的
`availability`、`verification`、deployment evidence 和 RLS 結果為準；不能依本文件
推測一個尚未連接的 provider 或 command 已經可用。
