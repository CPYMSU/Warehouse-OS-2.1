from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS_PAGE = ROOT / "frontend" / "v2" / "pages" / "pages-assets.jsx"
ASSETS_CSS = ROOT / "frontend" / "v2" / "pages" / "pages-assets.css"
ACTION_CENTER = ROOT / "frontend" / "v2" / "action-center.jsx"
INDEX = ROOT / "frontend" / "v2" / "index.html"
PERSONAL = ROOT / "frontend" / "v2" / "personal.html"
CORE = ROOT / "frontend" / "v2" / "core.jsx"
CORE_CSS = ROOT / "frontend" / "v2" / "core.css"
APP = ROOT / "frontend" / "v2" / "app.jsx"
LANG = ROOT / "frontend" / "v2" / "lang.jsx"
LOGS = ROOT / "frontend" / "v2" / "pages" / "pages-logs.jsx"
TASKS = ROOT / "frontend" / "v2" / "pages" / "pages-tasks.jsx"
TASKS_CSS = ROOT / "frontend" / "v2" / "pages" / "pages-tasks.css"


def test_assets_page_loads_all_existing_data_contracts():
    source = ASSETS_PAGE.read_text(encoding="utf-8")
    for endpoint in (
        "/api/assets",
        "/api/assets/portfolio",
        "/api/digital-assets?limit=300",
        "/api/digital-assets/summary",
        "/api/digital-assets/listings?status=listed&limit=100",
        "/api/digital-assets/common-market",
        "/api/digital-assets/trades?limit=50",
        "/api/digital-assets/revenue?limit=50",
        "/api/database-projects?limit=500",
        "/database/health",
        "/database/schema",
        "/database/onboarding",
        "/pages-console?limit=20",
    ):
        assert endpoint in source


def test_digital_assets_use_numbered_swiss_register_without_losing_actions():
    source = ASSETS_PAGE.read_text(encoding="utf-8")
    css = ASSETS_CSS.read_text(encoding="utf-8")

    assert "assets-poster-page" in source
    assert "asset-poster-nav" in source
    assert "asset-master-poster" in source
    assert "AssetOperationTopology" in source
    assert 'data-testid="asset-operation-topology"' in source
    assert "asset-flow-topology" not in source
    assert 'assets-${tab}-poster' in source
    assert '["09.1", "FINANCIAL ASSETS"' in source
    assert '["09.2", "DIGITAL CUSTODY"' in source
    assert '["09.3", "DATA ASSETS"' in source
    assert '["09.4", "DATABASE SERVICES"' in source
    assert '["09.5", "TRADING CENTRE"' in source
    assert "TAB_PLANES" in source
    assert "asset-plane-navigation" in source
    assert "digital-poster-register" in source
    assert "digital-poster-card" in source
    assert "digital-poster-detail" in source
    assert 'aria-pressed={!!selected}' in source

    for action in ("評估資產", "上架到市場", "訪問與收入"):
        assert action in source
    for selector in (
        ".asset-master-poster",
        ".asset-action-index",
        ".assets-poster-page > .folio",
        ".digital-poster-grid",
        ".digital-poster-card",
        ".digital-poster-custody",
        ".digital-poster-facts",
    ):
        assert selector in css
    assert "@media (max-width: 680px)" in css
    assert "prefers-reduced-motion" in css


def test_digital_asset_drawer_exposes_the_pages_hosting_console():
    source = ASSETS_PAGE.read_text(encoding="utf-8")
    css = ASSETS_CSS.read_text(encoding="utf-8")

    assert "const PagesConsole" in source
    assert 'data-testid="pages-hosting-console"' in source
    assert "發布歷史" in source
    assert "data.actions" in source
    assert "dispatchAction" in source
    assert 'invocation.mode === "auto_runtime"' in source
    assert "action_context: invocation.action_context" in source
    assert 'invocation.mode === "typed_action"' in source
    assert 'runtime.mode === "static_frontend_device_first"' in source
    assert 'deviceFirstPages ? "Pages 靜態"' in source
    assert 'pagesFrontend ? "用戶瀏覽器"' in source
    assert 't("設備可選 · 平台按需")' in source
    assert "不得使用已退役的 dm site rollback" not in source
    assert ".pages-console" in css
    assert ".pages-release-history" in css


def test_assets_poster_styles_are_loaded_and_cache_busted():
    index = INDEX.read_text(encoding="utf-8")
    assert 'pages/pages-assets.css?v=20260805-pages-console1' in index
    assert 'pages/pages-assets.jsx?v=20260806-pages-package1' in index
    assert 'pages/pages-logs.jsx?v=20260804-audit-conversation1' in index
    assert 'pages/pages-tasks.css?v=20260804-task-actions1' in index
    assert 'pages/pages-tasks.jsx?v=20260804-task-actions1' in index
    assert 'core.css?v=20260806-login-farmer1' in index
    assert 'core.jsx?v=20260806-pages-actions1' in index
    assert 'action-center.jsx?v=20260807-passkey-action1' in index
    assert 'pages/pages-research-continuity.css?v=20260807-continuity1' in index
    assert 'pages/pages-research-typography.css?v=20260807-autosize1' in index
    assert 'dist/app.bundle.js?v=20260808-civilization13' in index
    assert 'dist/personal.bundle.js?v=20260806-login-farmer1' in PERSONAL.read_text(
        encoding="utf-8"
    )
    assert 'core.jsx?v=20260806-pages-actions1' in PERSONAL.read_text(encoding="utf-8")


def test_login_poster_uses_bonfire_platform_identity_and_modular_motion():
    source = APP.read_text(encoding="utf-8")
    css = CORE_CSS.read_text(encoding="utf-8")

    assert "BONFIRE PLATFORM" in source
    assert "CONNECTED INTELLIGENCE" in source
    assert "LOGIN_MODULE_CELLS" in source
    assert 'className="login-module-field"' in source
    assert "像農民一樣思考。" in source
    assert "Warehousing<br/>is a business" not in source
    assert ".login-module-field" in css
    assert "@keyframes login-module-rise" in css
    assert "prefers-reduced-motion" in css


def test_audit_conversation_drawer_uses_native_detail_contract_and_truthful_errors():
    source = LOGS.read_text(encoding="utf-8")

    assert 'W2.json("/api/ai/conversations/" + encodeURIComponent(c.id))' in source
    assert "/api/ai/conversation?id=" not in source
    assert "對話內容讀取失敗" in source
    assert "重新讀取" in source
    assert "可能是後端未就緒或對話已歸檔" not in source


def test_task_cards_expose_complete_edit_and_confirmed_delete_actions():
    source = TASKS.read_text(encoding="utf-8")
    css = TASKS_CSS.read_text(encoding="utf-8")

    assert 'raw.can_status === true' in source
    assert 'raw.can_update === true' in source
    assert 'raw.can_delete === true' in source
    assert 'options.find(([status]) => status === "completed")' in source
    assert 'method: "PATCH"' in source
    assert 'method: "DELETE"' in source
    assert 'confirm: true' in source
    assert "TaskDeleteDialog" in source
    assert ".task-action-edit" in css
    assert ".task-delete-dialog" in css


def test_business_action_command_topology_exposes_runtime_execution_contract():
    source = ACTION_CENTER.read_text(encoding="utf-8")
    css = CORE_CSS.read_text(encoding="utf-8")

    assert "指令集拓撲" in source
    assert "action.execution_identity" in source
    assert "action.semantic_resource" in source
    assert "action.verification" in source
    assert "selected.confirmation_policy" in source
    assert "selected.adapter" in source
    assert 'className="business-action-contract"' in source
    assert ".business-action-contract" in css
    assert '"/propose"' in source
    assert "W2.OperationConfirmation" in source
    assert '"/execute-authorized"' in source
    assert 'className="business-action-authorization"' in source
    assert ".business-action-authorization-flow" in css


def test_secretary_dock_exposes_lighthouse_pairing_and_read_only_runs():
    source = CORE.read_text(encoding="utf-8")
    css = CORE_CSS.read_text(encoding="utf-8")

    assert 'W2.json("/api/lighthouse/devices")' in source
    assert 'W2.post("/api/lighthouse/pairing-challenges"' in source
    assert 'W2.json("/api/lighthouse/runs"' in source
    assert 'read_only: true' in source
    assert 'data-auto-runtime-card="execution-target"' in source
    assert 'aria-label={t("Auto Runtime 執行位置卡片")}' in source
    assert 'className="secretary-device-select"' not in source
    assert 'lh cloud-pair --warehouse-url' in source
    assert ".secretary-dock{width:" not in source
    assert ".secretary-dock.big{width:auto}" in source
    assert "width:min(900px,calc(100vw - 56px));box-sizing:border-box" in source
    assert ".dock.big { width: min(720px, calc(100vw - 56px)); }" in css
    assert ".secretary-dock .dock-scroll{height:585px;flex-basis:585px}" in source
    assert "height:min(78vh,960px);flex-basis:min(78vh,960px)" in source


def test_login_poster_uses_farmer_manifesto():
    app = APP.read_text(encoding="utf-8")
    catalog = LANG.read_text(encoding="utf-8")
    for line in ("像農民一樣思考。", "尊重規律，經營時間，", "讓每一份資源", "自然生長"):
        assert line in app
        assert line in catalog
    assert 'className="login-manifesto-title"' in app
    assert "Think like a farmer.<br/>Respect natural rhythms." in app
    assert "Steward time.<br/>Let every resource" in app
    assert "像农民一样思考。" in catalog
    assert "尊重规律，经营时间，" in catalog
    assert "一個入口，" not in app
    assert "One entry.<br/>Every possibility" not in app
    assert "連接人與 AI、知識、代碼、數據與行動。" not in app
    assert "倉儲," not in app
    assert "Warehousing<br/>is a business" not in app


def test_digital_custody_register_uses_restrained_ledger_treatment():
    source = ASSETS_PAGE.read_text(encoding="utf-8")
    css = ASSETS_CSS.read_text(encoding="utf-8")
    assert 'tab === "dig" ? " assets-poster-digital"' in source
    assert "Restrained custody register" in css
    assert ".assets-poster-digital .digital-poster-card" in css
    assert "grid-template-columns: 70px minmax(180px,.85fr)" in css
    assert ".digital-poster-card.is-selected::before" in css
    assert "background: transparent" in css
    assert "Selected custody language: B / collection label" in css
    assert "grid-template-columns: 52px minmax(220px,1.2fr)" in css
    assert "Typography and whitespace create the groups" in css


def test_empty_workspace_exposes_manual_and_ai_code_storage_switches():
    source = ASSETS_PAGE.read_text(encoding="utf-8")

    assert "digital_market_workspace_storage_switch" in source
    assert '"code-storage": targetCodeStorage' in source
    assert '"expected-revision"' in source
    assert "ws.code_storage_switchable === true" in source
    assert "尚未上傳源碼,可以直接切換" in source
    assert "已有源碼,不要直接改綁定" in source


def test_digital_custody_exposes_standalone_database_request_flow():
    source = ASSETS_PAGE.read_text(encoding="utf-8")

    assert "申請資料庫" in source
    assert "standaloneDatabasePrompt" in source
    assert "不部署 Runtime" in source
    assert "dm db service create" in source
    assert "dm db onboarding" in source
    assert "不要把 wak_ 或資料庫密碼交給對話或瀏覽器" in source


def test_data_and_database_are_independent_same_level_asset_planes():
    source = ASSETS_PAGE.read_text(encoding="utf-8")
    css = ASSETS_CSS.read_text(encoding="utf-8")

    assert '["fin", "金融資產"]' in source
    assert '["dig", "數字資產"]' in source
    assert '["data", "數據資產"]' in source
    assert '["db", "資料庫服務"]' in source
    assert '["trade", "交易中心"]' in source
    assert 'data-asset-plane={TAB_PLANES[id]}' in source
    assert 'params.set("plane", TAB_PLANES[id])' in source
    assert 'tab === "data"' in source
    assert 'tab === "db"' in source
    assert "database-service-drawer" in source
    assert "database-service-layout" in css
    assert "database-drawer" in css


def test_database_asset_plane_exposes_only_safe_onboarding_material():
    source = ASSETS_PAGE.read_text(encoding="utf-8")

    for safe_field in (
        "allowed_origins",
        "project_key",
        "sdk_url",
        "規則預設全部拒絕",
        "公開專案定位符",
    ):
        assert safe_field in source
    assert "憑證不會顯示在頁面" in source
    assert "不要把 wak_ 或資料庫密碼交給對話或瀏覽器" in source


def test_asset_operation_topology_merges_stages_clicks_and_ai_over_one_contract():
    source = ASSETS_PAGE.read_text(encoding="utf-8")
    css = ASSETS_CSS.read_text(encoding="utf-8")

    assert 'W2.json("/api/business/actions", { cache: "no-store" })' in source
    assert "const AssetOperationTopology" in source
    assert 'data-testid="asset-operation-topology"' in source
    assert "SWISS ACTION TOPOLOGY" in source
    assert "asset-flow-topology" not in source
    assert "asset-flow-topology" not in css
    assert "openTypedAction(spec.tool, argumentsValue)" in source
    assert "assistTypedAction(spec.tool, t(spec.label), argumentsValue)" in source
    assert "data-testid={`asset-action-manual-${spec.tool}`}" in source
    assert "data-testid={`asset-action-ai-${spec.tool}`}" in source
    assert "tool_name: toolName" in source
    assert 'filter: "authorized"' in source
    assert "safeAssistantArgs" in source

    for tool_name in (
        "asset_add",
        "asset_refresh",
        "asset_buy",
        "asset_analyze",
        "digital_market_create",
        "digital_market_upload",
        "digital_market_workspace_create",
        "digital_market_assess",
        "digital_market_listing_create",
        "digital_market_version_add",
        "digital_market_custody",
        "digital_market_database_project_create",
        "digital_market_console",
        "digital_market_database_browser_configure",
        "digital_market_database_onboarding",
        "digital_market_common",
        "digital_market_order_create",
        "digital_market_orders",
        "digital_market_trades",
        "digital_market_revenue_record",
    ):
        assert tool_name in source

    assert 'grid-template-columns: repeat(var(--asset-flow-count),minmax(0,1fr))' in css
    assert ".asset-action-card.state-confirm" in css
    assert ".asset-action-card.state-locked" in css
    assert ".asset-action-card.state-unavailable" in css
    assert ".asset-action-card > footer button.is-ai" in css
    assert "border-radius: 0" in css


def test_contextual_asset_actions_prefill_native_parameter_names():
    source = ASSETS_PAGE.read_text(encoding="utf-8")

    assert 'openTypedAction("digital_market_create", { kind: "data" })' in source
    assert '"asset-kind": "data"' not in source
    assert 'openTypedAction("asset_buy", { id: a.id })' in source
    assert 'openTypedAction("asset_sell", { id: a.id })' in source
    assert 'openTypedAction("asset_dividend", { id: a.id })' in source
    assert 'openTypedAction("digital_market_assess", { id: a.id })' in source
    assert 'openTypedAction("digital_market_listing_create", { id: a.id })' in source
    assert 'openTypedAction("digital_market_order_create", { listing: l.id })' in source
    assert '"allowed-origins": browser.allowed_origins || []' in source
    assert 'rules: databaseRules(project)' in source


def test_business_action_json_prefill_is_serialized_for_editable_fields():
    source = ACTION_CENTER.read_text(encoding="utf-8")

    assert 'typeof value !== "string"' in source
    assert 'JSON.stringify(value, null, type === "object" ? 2 : 0)' in source
    assert "value: inputValue" in source
