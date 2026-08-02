# V2 前端—新後端實作矩陣

本文件以 `frontend/v2/` 的現有頁面與互動為介面規格；不以「存在路由」
視為完成。每一項完成時都必須具備 PostgreSQL 持久化、租戶 RLS、有效身分
權限判斷、審計事件（寫入操作）與頁面實測。

## 已實作的最小基礎

| 前端入口 | 新後端狀態 | 說明 |
| --- | --- | --- |
| 登入、登出、目前帳號 | 已連線 | 全域帳密登入、舊 PBKDF2 雜湊升級、當前公司 JWT。 |
| 公司清單與切換 | 已連線 | 只回傳登入帳號自己的有效公司；切換時簽發目標公司的新 JWT。 |
| 產業模板、組織模板 | 部分連線 | 13 套模板與租戶快照已在 PostgreSQL。 |
| 啟動資料、倉庫地理資料 | 部分連線 | 真實空集合或已存資料，不注入展示資料。 |
| 公司總覽 | 部分連線 | GIS、組織權限、審計卡片讀取目前租戶的 PostgreSQL 資料；尚未有資料域的卡片明確標示不可用。 |
| 庫存、入庫、出庫、在途、GIS | 部分連線 | 已共用物資、批次、庫存流水、單據、調撥與借還資料表；前端啟動資料和快捷操作均走新 API。無業務資料時顯示真實空狀態。 |
| 超級終端、AI 工具目錄 | 已連線 | 478 條租戶指令保留作相容與能力檔案；已退役契約不可執行，也不向模型暴露。Auto Runtime 只啟用具備真實適配器、權限、RLS、審計及確認契約的能力。 |
| 數字資產託管 | 已連線 | 原生資產、工作區、永久入口、512 MiB 階梯配額、PostgreSQL Data API、主／附屬 `wak_` Key、不可變源碼版本、冪等部署、Runtime Controller、健康探測與永久入口切流已接通。 |

## 逐頁實作順序

| 階段 | 前端頁面／入口 | 主要 API 契約群 | 需建立的資料域 |
| --- | --- | --- | --- |
| 1 | `app.jsx`、`pages-dashboard.jsx` | auth、company、runtime、branding、overview | 全域帳號、公司會員、偏好、品牌、權限過濾總覽 |
| 2 | `pages-perms.jsx`、`pages-companies.jsx` | org、users、roles、permissions、platform tenants | 組織單位、職位、會員任命、角色、權限覆寫、平台治理 |
| 3 | warehouse tabs、`pages-gis.jsx` | warehouses、inventory、inbound、outbound、shipments、stocktake、GIS | 物資、批次、庫位、庫存流水、單據、盤點、調撥／運輸 |
| 4 | `pages-tasks.jsx`、`pages-records.jsx`、`pages-cases.jsx` | tasks、records、cases、notifications、collab | 任務、通用記錄、案例、附件、討論、通知 |
| 5 | `pages-procurement.jsx` | wf、procurement、tender | 工作流定義／實例／任務、採購申請、詢報價、合同銜接 |
| 6 | `pages-erp.jsx`、`pages-finance.jsx`、`pages-assets.jsx` | erp、ledger、assets、digital-assets | 會計科目、憑證、預算、應收應付、固定資產、數位資產 |
| 7 | `pages-legal.jsx`、`pages-reports.jsx` | legal、compliance、reports | 合同、印鑑、合規鏈、報表快照與匯出 |
| 8 | `pages-settings.jsx`、`pages-logs.jsx`、`pages-shield.jsx` | settings、integrations、audit、shield | 公司設定、整合密鑰引用、審計查詢、運維安全事件 |
| 9 | `core.jsx`、`pages-terminal.jsx`、`personal.jsx` | agent、voice、AI、personal | AI 執行記錄、附件、確認操作、個人空間（與公司資料分域） |

## 完成判定

每個前端 API 的完成狀態只可為：

1. **已連線**：前端讀寫真實 PostgreSQL 資料，RLS 與權限測試通過。
2. **唯讀連線**：前端可讀取真實資料，寫入流程尚未交付。
3. **未實作**：不得由假資料、靜默成功或空白成功回應偽裝。

平台 AI 可以閱讀全域的非機密指令與功能目錄，但任何業務資料查詢與執行都
必須以目前公司租戶上下文進行；跨公司資料不會透過本矩陣中的任何接口暴露。

目前第 3 階段已交付物資、批次、流水、入／出庫、跨倉在途、借還提醒與 GIS
讀取；第 6 階段的數字資產託管控制面、資料面與 Runtime 執行面已連線。應用
仍只有在 Runtime Controller 寫入 `ready + healthy` 且永久入口探測成功後才可
宣稱上線。AI 批量盤點仍屬未實作，不能宣稱已可用。
