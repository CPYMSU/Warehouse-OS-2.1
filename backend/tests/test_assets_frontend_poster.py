from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS_PAGE = ROOT / "frontend" / "v2" / "pages" / "pages-assets.jsx"
ASSETS_CSS = ROOT / "frontend" / "v2" / "pages" / "pages-assets.css"
ACTION_CENTER = ROOT / "frontend" / "v2" / "action-center.jsx"
INDEX = ROOT / "frontend" / "v2" / "index.html"


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


def test_assets_poster_styles_are_loaded_and_cache_busted():
    index = INDEX.read_text(encoding="utf-8")
    assert 'pages/pages-assets.css?v=20260803-assets-operation-topology2' in index
    assert 'pages/pages-assets.jsx?v=20260803-assets-operation-topology2' in index
    assert 'dist/app.bundle.js?v=20260803-assets-operation-topology2' in index


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
