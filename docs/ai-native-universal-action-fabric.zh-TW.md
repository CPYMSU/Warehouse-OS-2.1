# AI 原生通用行動層

## 目標

Warehouse OS 不應要求每一個欄位修改都有一條預先寫好的指令，也不應把 AI
限制成只能從目前帳號可執行的兩三個按鈕中選擇。系統應讓公司 AI 看見目前公司
完整的能力、資料語義、組織責任與業務狀態，由 AI 判斷如何完成目標；底層只保留
租戶隔離、資料完整性、併發一致性、憑證邊界與完整審計等不可被推理取代的約束。

```text
人的自然語言目標 / 手動頁面操作
        ↓
Auto Runtime：理解、觀察、主觀判斷、形成計畫
        ↓
能力解析器：專用能力 / 通用資料能力 / 尚缺能力
        ↓
必要時取得 Action Keychain（授權信號，不代替 AI 執行）
        ↓
AI 繼續執行一個或多個動作
        ↓
原生業務適配器 或 通用資料網關
        ↓
PostgreSQL RLS / 交易 / 不變量 / 審計 / Outbox
        ↓
AI 讀回結果、核對是否真正完成、決定下一步
```

## 一、信任 AI，但不把資料庫交給提示詞

### AI 擁有的判斷

- 看見目前公司全部能力的名稱、用途、狀態、所需資料及可能影響；能力不因當前
  使用者沒有權限而從 AI 的世界中消失。
- 看見目前公司完整的組織、多人多身分綜合權限、責任人、工作流與資料關係。
- 自主判斷應直接讀取、直接修改、組合多個動作、追問資料、要求人確認，或建議去找
  哪一個人協助。
- 自主判斷上下文展開深度；頂層只看能力地圖及當前目標，需要時才載入欄位、關係、
  歷史、文件與原始記錄。
- 專用指令不存在時，可選擇通用資料操作，不必把「缺指令」誤判成「不能完成」。

### 系統只保留的硬邊界

- 一個公司 AI 永遠只進入一個 `tenant_id` 的 RLS 會話，不能選擇或切換實體資料庫。
- AI 不能提交 DSN、schema、table、SQL、任意欄位名或另一公司的識別碼。
- 外鍵、唯一性、金額平衡、狀態版本、必要欄位與資料型別由資料庫及領域交易保證。
- 密鑰、Passkey、付款、權限根、正式過帳、外部部署等副作用必須經專用適配器；
  這不是否定 AI 判斷，而是避免只改一個欄位卻漏掉其他交易與外部系統。
- 所有讀寫都留下可關聯到對話、Runtime run、操作者與 AI 判斷依據的事件。

硬邊界不包含一份「某職位只能按某按鈕」的寫死白名單。職位、權限、風險、責任人
與公司規章作為 AI 的判斷證據存在；只有跨租戶、資料結構與憑證安全是不允許被推理
覆蓋的不變量。

## 二、三層能力解析

每個目標先由 AI 判斷應落入哪一層，程式不以大量 `if/else` 代替 AI 路由。

### A. 原生業務能力

適合會跨多張表、產生外部副作用或必須維持領域交易的操作，例如：

- 付款、收貨、正式 PO、財務過帳；
- 發行、輪換、撤銷 API Key；
- Passkey、角色根權限、租戶及平台治理；
- 部署、撤回部署、工作流節點遷移；
- 法律簽署、託管資產轉移。

原生能力的接口是交易邊界，不是 AI 的固定工作流程。AI 仍可自由選擇、組合、重試、
補充資料或中止。

### B. 通用資料能力

適合單一資源或一組可在同一交易中安全完成的結構化修改，例如：

- 修改資產分類、名稱、說明、標籤及普通設定；
- 編輯部門、崗位、聯絡資料與展示順序；
- 修改工作區的配置型欄位；
- 建立或修正尚未有專用指令的普通業務記錄。

AI 使用語義資源名及欄位 key，不接觸 SQL。資料網關解析成當前資料庫的物理存儲，
因此未來更換 PostgreSQL、拆服務或引入其他儲存時，AI、前端及外部 API 的契約不變。

### C. 尚缺能力

如果目標需要未知外部服務、無法表達的跨資源交易或尚未登記的資料語義，AI 應：

1. 清楚說明缺的是哪個能力，而不是宣稱操作成功；
2. 保存已取得的上下文與預期結果；
3. 自動建立一條 `capability_gap`，供開發者補成原生能力；
4. 若其中一部分可由通用資料能力完成，由 AI 判斷先完成可逆部分或等待整體能力。

## 三、資料庫驅動的語義資源註冊表

增加一個由資料庫管理的資源語義層。它描述「這是什麼」與「怎樣存」，不編寫使用者
意圖的決策樹。

### `app.resource_types`

| 欄位 | 作用 |
| --- | --- |
| `resource_key` | 穩定語義名，例如 `digital_asset.asset` |
| `version` | 契約版本 |
| `label` / `description` | 供人與 AI 理解 |
| `storage_adapter` | `postgres_table`、`document_projection`、`remote_service` |
| `storage_locator` | 僅服務器可讀的物理映射，永不傳給模型 |
| `identity_fields` | 可用 UUID、DMA 編號、workspace key 或名稱解析 |
| `lifecycle` | 可用狀態及其語義 |
| `active` | 是否可供 AI 解析與使用 |

### `app.resource_fields`

| 欄位 | 作用 |
| --- | --- |
| `field_key` | 穩定語義 key，例如 `runtime_type` |
| `data_type` / `format` | 型別及格式 |
| `required` / `nullable` | 結構約束 |
| `editable_mode` | `direct`、`adapter_only`、`derived`、`immutable` |
| `sensitivity` | 普通、個資、機密、憑證等資訊標記 |
| `semantic_description` | 欄位對業務的真實含義 |
| `examples` | 少量正反例，幫助 AI 判斷 |
| `storage_path` | 服務器內部映射，不暴露給模型 |

### `app.resource_relations` 與 `app.resource_invariants`

- 關係描述資產、工作區、版本、部署、帳款、PO、使用者、部門等如何相連。
- 不變量只保存必須始終成立的事實，例如「workspace 必須屬於 asset」或「版本必須
  屬於同一資產」，不保存僵硬的自然語言工作流程。
- `enforcement` 可為 `database`、`domain_adapter` 或 `external_verification`，讓 AI
  知道何處能直接修改、何處必須選擇原生能力。

十三種行業預設只需要種入資源語義、責任語義、常見關係與經驗提示，不需要複製十三
套後端代碼。每家公司可覆寫顯示名、責任位置、重要程度與 AI 提示；底層資源 key
保持穩定。

## 四、統一 Data API 2.1

提供一組與物理資料庫解耦的接口，供前端、Auto Runtime、超級終端及外部工作區共同
使用：

```http
GET  /api/data/v2/resources
GET  /api/data/v2/resources/{resource_key}/schema
POST /api/data/v2/query
POST /api/data/v2/resolve
POST /api/data/v2/mutations/preview
POST /api/data/v2/mutations/commit
POST /api/data/v2/transactions/preview
POST /api/data/v2/transactions/commit
```

通用修改使用語義 Patch：

```json
{
  "resource": "digital_asset.workspace",
  "ref": "mk4-workspace",
  "expected_version": 3,
  "changes": {
    "runtime_type": "web",
    "summary": "MK4 Web 與 API 工作區"
  },
  "intent": "把 MK4 從純靜態託管調整成可部署後端的 Web 工作區",
  "reasoning_summary": "使用者已明確指定目標；欄位為 direct，未觸發部署副作用",
  "run_id": "...",
  "idempotency_key": "..."
}
```

網關必須完成：資源解析、型別驗證、欄位模式核對、關係及不變量檢查、樂觀鎖、交易、
讀回核驗、RLS、敏感欄位遮罩、事件與 outbox。AI 不需要知道這些實作細節，但會收到
可理解的預覽、衝突、驗證失敗與完成結果。

`preview` 不等於固定要求確認。它是 AI 的觀察工具；AI 可根據差異、可逆性、目前使用者
身分、公司規章及上下文，主觀決定直接 `commit`、取得授權、改計畫或詢問人。

## 五、Action Keychain 是授權信號，不是執行按鈕

目前的 `secretariat.execution_keychains` 方向正確，但 scope 應從「只允許執行某一條
預存命令」升級成可描述一個不可擴張的行動包：

```json
{
  "goal_digest": "...",
  "resources": [
    {"resource": "digital_asset.workspace", "refs": ["mk4-workspace"]}
  ],
  "allowed_effects": ["update", "deploy", "issue_delegated_key"],
  "field_scope": ["runtime_type", "runtime_status", "components"],
  "limits": {"max_actions": 6, "expires_in_seconds": 1200},
  "prohibited_effects": ["delete_asset", "rotate_primary_key"]
}
```

Passkey 驗證成功後：

1. 卡片狀態變成 `authorized`；
2. 後端把 keychain 返回 Auto Runtime；
3. 卡片本身不調用業務接口；
4. AI 重新觀察最新狀態，在 scope 內自由完成一個或多個步驟；
5. 每一步使用同一 keychain 但遞增使用序號，達到上限或完成目標後關閉；
6. AI 核驗實際結果後才把卡片標記為完成。

這可避免先建工作區、再簽 Key 時第二張卡片因前一步尚未執行而得到
`Workspace not found`，也符合「人授權目標，AI 負責執行計畫」的操作方式。

## 六、通用操作的完整審計與能力回流

新增 `secretariat.data_mutations`，每次通用資料操作至少記錄：

- `tenant_id`、`run_id`、`conversation_id`、操作者及執行身分；
- `resource_key`、資源 ref、變更欄位、`before` / `after` 或其安全摘要；
- AI 的 `intent`、`reasoning_summary`、觀察證據指標；
- `origin = generic_mutation`、`coverage = command_missing`；
- 預覽版本、提交版本、idempotency key、keychain、Passkey 驗證摘要；
- 執行狀態、失敗原因、讀回核驗結果與補償狀態。

新增 `terminal.capability_gaps`：

| 欄位 | 作用 |
| --- | --- |
| `fingerprint` | tenant + resource + effect + field set 去重 |
| `occurrence_count` | 發生次數 |
| `first_seen_at` / `last_seen_at` | 使用時間 |
| `examples` | 去敏後的真實目標與結果 |
| `suggested_tool_name` | AI 建議的未來能力名 |
| `promotion_reason` | 頻繁、跨資源、需副作用、錯誤率高等原因 |
| `status` | observed、reviewing、promoted、dismissed |
| `promoted_tool_name` | 補成專用能力後的對應關係 |

通用操作不因為沒有指令而被視為次等或失敗。只有當它變得頻繁、需要跨資源交易、
涉及外部副作用或反覆出錯時，才由數據證據建議開發者提升成原生能力。

## 七、AI 的判斷上下文

Auto Runtime 的多層蒸餾增加兩個可按需展開的索引：

- `L0 Resource Atlas`：只有資源名、含義、關係摘要及支持的 effect；所有資源可見。
- `L3 Resource Contract`：AI 選中資源後才載入精確欄位、關係、不變量、當前版本及
  可用適配器。

AI 在每次行動前收到的是證據而不是結論：

```json
{
  "native_capability": null,
  "generic_mutation_available": true,
  "resource": "digital_asset.workspace",
  "effects": ["update"],
  "editable_fields": ["runtime_type", "summary"],
  "adapter_only_fields": ["runtime_status"],
  "responsible_people": ["..."],
  "current_actor_identities": ["..."],
  "company_guidance": ["..."],
  "hard_invariants": ["workspace belongs to asset"],
  "unknowns": []
}
```

模型自行形成「可以做、先詢問、找誰、需要授權或不能完成」的判斷。服務器不預先替
模型寫一套固定答案，也不因為當前人沒有某個權限而把能力與責任人資訊隱藏。

## 八、MK4 的預期行為

使用者說「把 MK4 託管類型改成 Web / API」時：

1. AI 從資產編號、名稱及對話上下文解析到 `mk4-workspace`；
2. 讀取 workspace schema 及當前版本；
3. 發現 `runtime_type` 是可通用修改的配置欄位，直接改為 `web` 或 `api`；
4. 發現真正部署需要 source version、runtime、entrypoint 與部署適配器；
5. AI 說明配置已改，但部署尚未完成，並追問或尋找源碼；
6. 取得源碼後選擇原生部署能力；若需要人授權，取得 keychain 後由 AI 繼續完成；
7. 審計把第一步標成 `generic_mutation / command_missing`，並建立是否需要補
   `dm workspace update` 的能力缺口建議。

這樣既不會把「修改類型」錯誤理解成「改名稱」，也不會把一條 planned 記錄說成後端
已部署完成。

## 九、與現有 2.1 架構的銜接

- 保留 `Auto Runtime`、能力 Atlas、L0-L6 多層上下文與公司 AI 身分。
- 保留原生 FastAPI 路由優先的原則。
- 將目前 `compatibility.documents` 的命令投影網關降為過渡適配器；新通用資料網關
  直接依資源註冊表讀寫正式領域表，不能再把每個 API 只投影成 JSON 文件。
- `terminal.command_executions` 繼續記專用指令；通用資料修改寫入
  `secretariat.data_mutations`，兩者以 `run_id` 和 `operation_id` 串成同一條時間線。
- `secretariat.execution_keychains` 升級為多步驟 action envelope，卡片只授權，Runtime
  才執行。
- 前端手動表單與 AI 使用同一份資源 schema；表單只是 schema 的人類渲染，不再維護
  另一套欄位與驗證規則。

## 十、建議實作順序

1. 建立資源註冊表、通用 mutation ledger、capability gap 與完整 RLS。
2. 建立 Data API 2.1 的 schema、resolve、query、preview、commit 與 transaction。
3. 先註冊 `digital_asset.asset`、`digital_asset.workspace`、`iam.organizational_unit`、
   `iam.position_profile` 四種資源，驗證 MK4 及權限拓撲編輯。
4. 把 Auto Runtime 的 capability resolver 加入 `generic_data` 路徑和 Resource Atlas。
5. 將 keychain 改為 action envelope，支援 AI 授權後續跑與多步驟配額。
6. 讓業務操作拓撲及普通編輯表單由同一份 schema 自動生成。
7. 逐步把 compatibility 投影升級到正式資源；依 capability gap 的真實使用量決定哪些
   操作值得提升成專用指令。

驗收時不以「接口返回 200」為完成，而以：AI 是否找到正確資源、是否完成真正資料
變更、是否讀回核驗、是否保持公司隔離、是否留下可理解審計，以及無專用指令時是否
仍能誠實完成可完成的部分為準。

## 十一、通用 Claim–Evidence 閉環

Auto Runtime 不按「下載、部署、Key」等自然語言關鍵字編寫完成規則。路由、能力選擇、
參數推導、是否繼續與證據含義仍由模型判斷；服務器只執行一套跨領域的證據協議：

1. 每個目前公司上下文與能力結果取得穩定 `evidence_id`，並標明來源是人的陳述、目前
   公司觀察或能力執行結果。人的陳述可用於解析目標，但不自動成為外部現實證明。
2. 反思層為每項重要主張返回 `statement`、`requires_evidence` 與 `evidence_refs`。目前
   世界狀態、行動結果、既有交付物及可用資源位置必須引用證據；一般推理與建議可以不
   引用目前世界證據。
3. `interaction_mode=operational` 是模型選出的認知狀態，但其服務器語義固定為必須進入
   能力／證據循環。計畫層不能在零觀察、零執行時自行宣告完成。
4. 原本被路由為知識回答的內容仍經第二視角反思。若反思判斷需要目前證據，可自行提出
   `next_domains`、`next_families` 或 `next_decisions`，重新進入同一能力循環，不需要為
   特定業務增加分支。
5. 最終文字中的 HTTP(S) 地址及站內資源路徑只能精確重用人的輸入、目前公司觀察或能力
   結果中已出現的地址。可以由正式站內相對路徑生成同源絕對地址，但不得延伸、拼接或
   猜測子路徑。
6. 語言修復之後再次執行證據核對，避免翻譯／潤色階段重新引入未觀察事實。若證據仍不
   足，Runtime 會將目標標記為未完成、停止記憶候選，並以證據不足結果取代推測內容。

這個閉環同時約束文件交付、網址、部署、付款、通知、憑證及其他外部世界結果；新增領域
只需註冊能力與語義契約，不需要在 Runtime 中增加新的自然語言判斷樹。
