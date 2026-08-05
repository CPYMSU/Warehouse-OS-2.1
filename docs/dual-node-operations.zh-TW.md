# Bonfirework 雙節點操作契約

生產叢集由 `mac-primary` 與 `vultr-standby` 組成。兩個節點執行同一個
release，但資料庫遵守 single-writer：任何時刻只有一個節點接受寫入。

節點的目標角色不等於當下的資料寫入方向。正式切換前，Vultr 仍是唯一 writer，
Mac 是 logical subscriber；只有完成停寫、追平、sequence 同步與驗證後，才把
Mac 提升為 writer。不得同時讓兩端接受寫入，PostgreSQL logical replication
不是衝突自動合併的 active-active 系統。

## 資料同步與動態資料庫

控制資料庫與每個 `whdb_<32 hex>` 託管資料庫各自使用 PostgreSQL 18 logical
subscription。Tailscale 僅承載私有資料庫流量，資料庫埠不對公網開放。DDL、
sequence、large object 與新建資料庫不由 logical replication 自動複製，因此由
控制腳本補齊：

```bash
# 在目前 writer 建立發布、最小權限角色、sequence 權限與 replica identity
REPL_PASSWORD=... ops/cluster/configure-control-publication
REPL_PASSWORD=... ops/cluster/configure-hosted-publications

# 在 Mac 發現並建立新託管資料庫、三種隔離角色與 schema
ops/cluster/reconcile-hosted-databases-macos

# 僅在已驗證備份且應用停寫後首次建立 43+ 個 subscription
WAREHOUSE_CONFIRM_RESEED=YES ops/cluster/initialize-hosted-subscriber-macos

# 初次同步完成、每次 planned failover 前再次同步 sequence 水位
ops/cluster/sync-sequences-macos all

# 正式切換前鎖住 Mac 應用角色；fence 舊 writer 後才可解除
ops/cluster/set-macos-write-policy standby
WAREHOUSE_CONFIRM_PROMOTION=YES ops/cluster/set-macos-write-policy primary

# 聚合驗證控制與所有託管 subscription、table state 及 apply worker
ops/cluster/verify-replication-macos
```

`reconcile-hosted-databases-macos` 對資料庫 ID、owner、角色名稱及 schema 簽章採
fail-closed。若 publisher 在 database provisioning 期間改變 schema，只能重建
「尚無 subscription」的指定 Mac 資料庫：

```bash
WAREHOUSE_REBUILD_UNSUBSCRIBED=YES \
WAREHOUSE_REBUILD_DATABASE=whdb_<32 hex> \
  ops/cluster/reconcile-hosted-databases-macos
```

已有 subscription 的資料庫永遠不由對帳器自動刪除。新增 DDL 必須先以
expand/contract migration 同時部署兩端，再 refresh publication；新資料庫則先
對帳 schema，再建立獨立 subscription。

首次大量複製若遇到大型租戶，可增加
`WAREHOUSE_SUBSCRIPTION_WAIT_ATTEMPTS`（每次間隔 5 秒）。只有在同一維護窗口已
完整通過所有 schema 簽章檢查後，續跑才可設定
`WAREHOUSE_REUSE_SCHEMA_PREFLIGHT=YES`；一般排程不得跳過全量預檢。

## 正式切換 writer

1. 保持公開流量在 Vultr，Mac 應用服務關閉或不可寫。
2. 確認控制資料庫 156/156、全部託管資料庫 publication tables 均為 `r`。
3. 暫停 Vultr 寫入，等待 subscriber LSN 追平且 slot retained WAL 接近零。
4. 執行 `sync-sequences-macos all`，比對關鍵表筆數與 Alembic head。
5. 停用 Vultr→Mac subscriptions，將 Mac 提升為唯一 writer。
6. 設定 `WAREHOUSE_CONFIRM_PROMOTION=YES` 並切換 Mac write policy 為 `primary`。
7. 啟動 Mac 應用並驗證 private origin，再切 Cloudflare 正式流量。
8. 反向設定 Mac→Vultr replication，Vultr 驗證完成後才成為 standby。

自動故障切換仍須 fencing：系統必須先證明舊 writer 已停止接受寫入，才允許另一
端提升。網路分割時寧可短暫停止寫入，也不能形成 split-brain。

## 每次發布

1. CI 分別建置 `linux/amd64` 與 `linux/arm64`。
2. 兩種架構全部成功後，發布同一 SHA 的 multi-platform images。
3. 先部署 `vultr-standby`，確認 readiness、資料庫與 peer inventory。
4. 允許短暫 release skew，但不允許 schema skew。
5. 再部署 `mac-primary`。
6. `verify-nodes.py` 要求 release、Alembic head、角色、平台及 peer 全部一致。

任何步驟失敗都停止後續部署。應用回滾不自動執行資料庫 downgrade；migration
必須維持 expand/contract 相容。

## 必要環境變數

每個節點的 API/Runtime 都必須設定：

```text
WAREHOUSE_NODE_ID=mac-primary | vultr-standby
WAREHOUSE_NODE_ROLE=primary | standby
WAREHOUSE_NODE_PLATFORM=linux/arm64 | linux/amd64
WAREHOUSE_CLUSTER_PEERS=另一節點 ID
WAREHOUSE_RELEASE_ID=不可變 release ID
WAREHOUSE_GIT_SHA=完整 Git SHA
WAREHOUSE_ALEMBIC_HEAD=目前 Alembic head
```

公開的 `/api/system/cluster` 與 `/api/system/readiness` 不得回傳密碼、連線字串、
內部 IP 或其他秘密。

## GitHub Environment

`production-cluster` 預設應啟用 required reviewers。只有在以下變數設為 `true`
後，workflow 才會接觸正式節點：

```text
WAREHOUSE_DUAL_NODE_ENABLED=true
```

部署金鑰必須是 restricted deploy identities，不能提供一般 root shell。
