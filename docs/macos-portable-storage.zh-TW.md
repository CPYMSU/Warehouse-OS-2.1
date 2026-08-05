# Mac mini 可遷移儲存規格

正式資料根目錄固定為 `/Volumes/BonfireworkData`。應用程式只認這個穩定掛載點，底層 SSD 更換時不修改資料模型或 API。

## 安全條件

- 使用兩顆同型號、同容量 NVMe SSD 的 RAID 1。
- 優先使用 Thunderbolt 3/4；避免以一般 USB Hub 承載資料庫。
- 不接受 RAID 0 或單純 JBOD 作為 PostgreSQL 主儲存。
- RAID 不是備份；備份必須位於另一實體裝置，並複製至 Vultr 或物件儲存。
- PostgreSQL 運行中不得用 Finder、`cp` 或一般檔案同步搬移 PGDATA。

## 上線流程

1. 連接外接盒，以「磁碟工具程式 → RAID 輔助程式」建立鏡像 RAID，命名為 `BonfireworkData`。
2. 執行 `ops/storage/macos-storage check`。只有輸出 `storage_status=ready` 才能繼續。
3. 執行 `ops/storage/macos-storage plan` 保存裝置 UUID、容量及目標路徑證據。
4. 建立並校驗 PostgreSQL logical backup；啟用 WAL/PITR 後再進行維護窗口搬移。
5. 停止寫入，使用保留 owner、ACL、extended attributes 且帶 checksum 驗證的複製程序搬移兩個 PGDATA。
6. 修改 LaunchAgent 的 PGDATA，啟動兩套 PostgreSQL，檢查 migration、資料庫數量及應用 readiness。
7. 原路徑至少保留一個完整備份週期，確認 Vultr standby 可追上後才清理。

目前工具故意只提供 `check` 與 `plan`。實際 `apply` 必須在外接 RAID 已出現、備份驗證完成及維護窗口建立後才加入，避免在系統碟上誤操作。
