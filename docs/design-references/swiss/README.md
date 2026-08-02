# Swiss Frontend Reference Library

這個目錄是 Warehouse OS 2.1 的 Swiss／International Typographic Style 前端參考庫。它不是生產依賴，也不會被前端 bundle 載入；目的是讓後續設計有固定、合法、可追溯的代碼母本，而不是每次重新搜索或依賴來源不明的截圖。

## 快速入口

- `studies/index.html`：本項目原創、可直接以瀏覽器打開的四個 Swiss 網頁構圖習作。
- `../../../frontend/v2/design-lab/digital-custody/index.html`：數字資產托管 A／B／C／D 四個可部署的極簡 HTML Demo；只作設計評審，不載入正式頁面。
- `upstream/swiss-confederation/`：瑞士聯邦官方 Design System 的網格、字體、色彩與 spacing 原始碼節選。
- `upstream/swiss-post/`：Swiss Post Design System 的表格、tabs、focus 與 grid 原始碼節選。
- `upstream/raster/`：Raster 的 CSS Grid 與 International Typographic Style poster 範例。
- `UPSTREAM.lock.md`：來源網址、固定 commit、擷取日期與檔案範圍。
- `ATTRIBUTION.md`：授權及使用邊界。

## 經核驗的來源

| 來源 | 保存價值 | 授權 |
|---|---|---|
| [Swiss Confederation Design System](https://github.com/swiss/designsystem) | 官方 HTML/CSS、四欄與十二欄 responsive grid、字體與 spacing token | MIT；政府標誌與 favicon 排除 |
| [Swiss Post Design System](https://github.com/swisspost/design-system) | 可訪問性、表格密度、focus ring、元件與 layout 契約 | Apache-2.0 |
| [Raster](https://github.com/rsms/raster) | 極簡描述式 CSS Grid、responsive span 與 Swiss poster 示例 | MIT |

## 大師方法如何轉譯為介面

這裡只研究方法，不保存或複製受版權保護的海報圖像。

1. Josef Müller-Brockmann：先定網格，再讓內容決定跨欄；對齊比裝飾重要。
2. Emil Ruder：字級、行距、行長與空白共同建立閱讀秩序；不要把 metadata 當裝飾噪音。
3. Armin Hofmann：用比例、明暗和單一信號色形成張力；同一畫面不需要多個強調中心。
4. Max Bill：系統必須能從規則推演，而不是靠逐卡手調。

## Warehouse OS 使用紀律

- 先把頁面寫成黑白，再加入一個信號色。
- 一個畫面只允許一個最大字級與一個主要動作。
- 資料列優先使用共同基線；只有需要比較的數值才放大。
- 不用圓角、投影、漸變或裝飾性玻璃效果補救層級。
- 操作存在不代表都要同時突出；高頻主操作在第一層，其餘使用文字式次操作。
- 色彩必須帶語義：紅＝索引／警示，黃＝下一步／待處理，藍＝受控工作面。
- 每個 responsive breakpoint 都重新安排閱讀順序，而不只是把桌面網格壓窄。

## 更新方式

先核驗上游授權，再更新 `UPSTREAM.lock.md` 的 commit。品牌標誌、商標、專有字體和圖片不應複製進此目錄。
