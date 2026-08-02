from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS_PAGE = ROOT / "frontend" / "v2" / "pages" / "pages-assets.jsx"
ASSETS_CSS = ROOT / "frontend" / "v2" / "pages" / "pages-assets.css"
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
    ):
        assert endpoint in source


def test_digital_assets_use_numbered_swiss_register_without_losing_actions():
    source = ASSETS_PAGE.read_text(encoding="utf-8")
    css = ASSETS_CSS.read_text(encoding="utf-8")

    assert "assets-poster-page" in source
    assert "asset-poster-nav" in source
    assert "asset-master-poster" in source
    assert "asset-flow-topology" in source
    assert 'assets-${tab}-poster' in source
    assert '["09.1", "FINANCIAL ASSETS"' in source
    assert '["09.2", "DIGITAL CUSTODY"' in source
    assert '["09.3", "TRADING CENTRE"' in source
    assert "digital-poster-register" in source
    assert "digital-poster-card" in source
    assert "digital-poster-detail" in source
    assert 'aria-pressed={!!selected}' in source

    for action in ("評估資產", "上架到市場", "訪問與收入"):
        assert action in source
    for selector in (
        ".asset-master-poster",
        ".asset-flow-topology",
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
    assert 'pages/pages-assets.css?v=20260802-assets-collection5' in index
    assert 'pages/pages-assets.jsx?v=20260802-assets-collection5' in index
    assert 'dist/app.bundle.js?v=20260802-assets-collection5' in index


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
