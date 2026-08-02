# Warehouse OS《託管應用技術要求 2.2》

文件狀態：正式技術契約<br>
契約識別：warehouse.hosting-application.v2.2<br>
適用範圍：數字資產工作區、官方 dm.py、AI 秘書、自動化部署程序

這份標準定義「應用交付什麼」以及「平台保證什麼」。它不是特定框架教學。符合契約的 Python、Node.js、靜態網站、容器或 Compose 專案，應能由同一套 CLI、API 與 AI 秘書流程反覆部署並取得可驗證結果。

## 01 · 最小交付契約

一個可託管專案必須滿足：

1. 源碼以 ZIP 或 TAR 系列封裝，不能包含絕對路徑、父目錄穿越、裝置文件或逃逸連結。
2. 可由顯式設定或平台偵測得到唯一的啟動入口。
3. HTTP 服務監聽平台注入的 PORT，並監聽 0.0.0.0。
4. 提供不依賴登入的健康檢查路徑；推薦 /healthz。
5. 把源碼視為唯讀，把持久資料寫入 /workspace/data。
6. 依賴、執行時版本、建置與啟動命令必須可重現。
7. 機密只從環境變數或平台 Secret 取得，不得寫入源碼、日誌或回應。
8. 資料庫連線只讀取 DATABASE_URL；遷移必須可重入、可追蹤並具失敗邊界。
9. 收到終止信號後停止接收新工作、完成短任務並正常退出。

平台只有在「進程運行、健康檢查通過、公開路由驗證成功」三項事實同時成立時，才能把部署標記為 ready。

## 02 · 建議的專案描述文件

專案根目錄可加入 warehouse.hosting.json。缺少描述文件時平台仍可偵測，但正式環境建議顯式宣告。

~~~json
{
  "schema": "warehouse.hosting-application.v2.2",
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
    "database_url_env": "DATABASE_URL"
  },
  "deployment": {
    "activate_when_healthy": true
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
| 系統臨時目錄 | 可寫但不保證跨部署保存 |
| DATABASE_URL | 平台資料庫連線，由環境注入 |
| Workspace Key | 控制面認證；不應提供給應用前端 |

應用不能依賴目前工作目錄恰好等於源碼根目錄；路徑應以應用根目錄或平台變數解析。

## 06 · 資料庫與遷移

1. Schema 變更使用具版本的 migration，不以手工 SQL 取代。
2. 遷移在新的應用版本接流量前執行，失敗則不得啟用部署。
3. 擴展與收縮分開進行，避免新舊版本短暫並行時互相破壞。
4. 大表操作應分批，並聲明逾時、鎖定和回復策略。
5. 原生 SQL 必須使用驅動可接受的執行介面；含 JSON 冒號的 SQL 不應被誤解析為綁定參數。
6. 不把密碼、完整連線字串或個資輸出到 migration 日誌。

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
5. 注入 PORT、DATABASE_URL、工作區路徑及已授權 Secret。
6. 以唯讀源碼和可寫資料卷啟動隔離進程。
7. 執行健康檢查，再驗證公開入口確實路由至該部署。
8. 只有通過全部門檻才啟用；失敗時保留前一個健康版本。
9. 回傳階段、證據、錯誤代碼和經遮罩的日誌，不用籠統的成功訊息取代事實。
10. 健康檢查必須包含實際寫入探針；僅存在配置或資料列不等於儲存可用。

## 10 · 上線前檢查表

- [ ] 壓縮包可安全解封，服務端 SHA-256 與本地一致
- [ ] 描述文件或偵測結果只有一個明確入口
- [ ] 依賴有 lockfile，建置不需互動
- [ ] 服務監聽 0.0.0.0:$PORT
- [ ] health_path 在未登入狀態返回 2xx
- [ ] 持久寫入只進入 /workspace/data 或平台資料庫
- [ ] Secret 未進入源碼、前端資產與日誌
- [ ] migration 可重入，失敗不接流量
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
~~~

AI 秘書可使用「dm hosting requirements」能力，把 Markdown 與 JSON 下載卡直接交給使用者。文件與契約使用同一版本號；任何破壞相容性的要求都必須提升契約版本。
