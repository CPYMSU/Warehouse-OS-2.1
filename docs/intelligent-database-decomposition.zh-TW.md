# Warehouse OS 2.1：智能資料解構與原子恢復

## 目的

系統不把 AI 限制在預先寫死的工作流內。Auto Runtime 先理解目標，再觀察公司內的語義世界，自主決定要使用專用能力、通用資料能力、繼續觀察或詢問人類。

計畫屬於 AI，不屬於程式碼。程式碼只提供：可觀察事實、可用能力、資料不變量、租戶隔離、確認與審計邊界。

## 語義資源圖

`app.resource_types`、`app.resource_fields`、`app.resource_relations` 與 `app.resource_invariants` 共同描述 AI 可理解的世界。新增資源或關係後，`data observe` 會自然展開，而不需要增加一條「先查 A、再查 B」的固定流程。

數字資產世界目前包含：

- 資產、工作區、版本與托管交付物
- 前端/後端組件、儲存與資料庫綁定
- 主 Key / 附屬 Key 的非敏感生命週期資訊
- 部署請求、來源版本、健康狀態與經驗證公開網址

每個實體都保留資源類型、UUID、穩定引用與關係。工作區 key 不會被誤當成資產 ID；AI 若從工作區開始，應沿 `belongs_to_asset` 關係取得同一項資產，而不是猜測或建立替代資產。

## 世界觀察，不是工作流

領域能力與 `data observe` 返回 `warehouse.world-observation.v1`：

- primary / related entities
- verified facts
- uncertainties
- affordances
- `decision_owner: auto_runtime`
- `workflow_prescribed: false`

這些內容是 AI 判斷的證據，不指定下一步。字串式 `next_action` 只保留給舊客戶端相容，不是 Auto Runtime 的控制流。

## 所有失敗的通用恢復面

每個失敗的能力調用會返回 `warehouse.atomic-recovery.v1`。它向 AI 暴露四種通用工具：觀察關係圖、讀取資源 schema、查詢資料、預覽或提交直接欄位修改。

這不是自動 fallback，也不會強迫 AI 依序執行。AI 可依目標和新證據自行選擇是否使用。若通用修改成功，系統會保存意圖、判斷摘要、前後差異、版本、讀回核驗與能力缺口，供開發者日後把高頻操作提升為專用能力。

## 不可突破的治理外殼

以下限制不屬於業務流程，不能交由資料庫欄位繞過：

- 公司資料絕對按 tenant 隔離。
- 憑證明文與雜湊不進入 AI 語義世界。
- 資源身份必須持續一致，不能因一次 404 建立替代實體。
- 不可變托管證據使用專用適配器與審計鏈。
- `deployment.ready`、health 與 public URL 必須來自部署提供者、反向代理和探活證據；不能只改資料庫便宣稱網站已上線。

因此，「把 runtime_type 從 static 改為 api」可在原子資料層完成；「真正部署完成並可訪問」仍需執行外部部署和驗證，再把證據寫回。

## 重複資產防護

上傳到既有項目時必須傳入 `asset_ref` 或 `workspace_ref`。服務端會沿工作區關係解析並交叉核對資產。只有 AI 已判斷使用者明確要求建立新資產時，才接受 `create_new_asset: true`。

新資產的交付物雜湊會在建立主檔前驗證；同一資產與同一 workspace key 的建立請求具備冪等性。這可阻止來源上傳失敗後遺留 `*-source` 孤兒資產，也避免 runtime 升級誤建工作區。
