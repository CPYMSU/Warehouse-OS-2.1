from pathlib import Path

from app.services.organization import NAV_PERMISSION_RULES, NAVIGATION_CATALOG
from app.templates.industry_blueprints import nav_modules_for_permissions

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization.jsx"
STYLE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization.css"
MOBILE_PAGE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization-mobile.jsx"
MOBILE_STYLE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization-mobile.css"
APP = ROOT / "frontend" / "v2" / "app.jsx"
INDEX = ROOT / "frontend" / "v2" / "index.html"
PUBLIC_PAGE = ROOT / "frontend" / "v2" / "civilization-public.html"
PUBLIC_SCRIPT = ROOT / "frontend" / "v2" / "pages" / "pages-civilization-public.js"
PUBLIC_STYLE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization-public.css"
POSTCARD = ROOT / "frontend" / "v2" / "pages" / "civilization-postcard.js"
SCHEMA_MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "20260807_0083_civilization_thoughts.py"
)
EMPTY_DATA_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "20260807_0084_civilization_empty_data.py"
)
PUBLISHING_MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "20260808_0085_civilization_publishing.py"
)
PUBLIC_SHARING_MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "20260808_0086_civilization_public_shares.py"
)
COMPANY_PRESET_MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "20260808_0087_civilization_company_preset.py"
)


def test_civilization_navigation_sits_between_records_and_settings() -> None:
    ids = [str(item["id"]) for item in NAVIGATION_CATALOG]

    assert ids.index("cases") < ids.index("civilization") < ids.index("settings")
    assert NAV_PERMISSION_RULES["civilization"] == ("civilization.read",)
    assert "civilization" in nav_modules_for_permissions({"civilization.read"})
    assert "dashboard" not in nav_modules_for_permissions({"civilization.read"})
    assert "civilization" not in nav_modules_for_permissions({"overview.read"})


def test_civilization_page_registers_all_three_swiss_views() -> None:
    source = PAGE.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")

    assert 'window.W2.PAGES["civilization"] = Page' in source
    assert '[["a", "問題拓撲"], ["b", "思想時間軸"], ["c", "閱讀海報"]]' in source
    assert "w2_civilization:v1:" in source
    assert 'W2.json("/api/civilization/thoughts"' in source
    assert 'W2.post("/api/civilization/thoughts"' in source
    assert 'method: "PATCH"' in source
    assert "expected_revision" in source
    assert '"/draft"' in source
    assert '"/publish"' in source
    assert "contentLocale" in source
    assert "readingSections" in source
    assert "civ-article-section" in source
    assert "civilization_api_key_issue" in source
    assert "civilization-notes-close" in source
    assert "civilization-notes-open" in source
    assert "notes_open" in source
    assert '"/share"' in source
    assert "public_share_enabled" in source
    assert "CivilizationPostcard.downloadLong" in source
    assert "civ-share-card" in source
    assert ".civ-reader.is-notes-collapsed" in style
    assert "civ-lens-editor" in source
    assert "civilization-relations-editor" in source
    assert "relations: relations.map" in source
    assert ".civ-relation-editor-row" in style
    assert "civ-poster-index" in source
    assert 'className="civ-detail-quote"' in source
    assert 'String(selectedContent.quote || "").trim()' in source
    assert 'quote: "", sections: []' in source
    assert ".civ-detail-quote" in style
    assert "12 COLUMN SYSTEM" in source
    assert "BUILTIN_THOUGHTS" not in source
    assert "const drafts" not in source
    assert ".civ-atlas-layout" in style
    assert ".civ-chronology" in style
    assert ".civ-reader" in style
    assert "civ-poster-motion" in source
    assert 'className="civ-mast-word"' in source
    assert 'className="civ-mast-word-bars"' in source
    assert "civ-word-color-pass 7.2s" in style
    assert 'className="civ-mast-word-layer civ-mast-word-offset is-red"' in source
    assert 'className="civ-mast-word-layer civ-mast-word-offset is-blue"' in source
    assert 'className="civ-mast-word-layer civ-mast-word-offset is-green"' in source
    assert "animation-name: civ-word-register-red" in style
    assert "animation-name: civ-word-register-blue" in style
    assert "animation-name: civ-word-register-green" in style
    assert "height: 7px" in style
    assert "#DC2A20 0 18%, #F5D20A 18% 36%, #2161A9 36% 56%" in style
    assert "font-size: .44em" in style
    assert "max-width: 100%; font-size: .38em" in style
    assert ".civ-mast-word-color, .civ-mast-word-offset, .civ-mast-word-bars b { animation: none; opacity: 0; }" in style
    assert "data-domain" in source
    for domain in ("judgement", "technology", "organization", "time", "ethics"):
        assert f".civ-poster-motion.is-{domain}" in style
    assert "civ-poster-opposition" not in style
    assert ".civ-poster-motion { display: none; }" in style
    assert "@media (prefers-reduced-motion: reduce)" in style


def test_civilization_assets_are_in_the_production_manifest() -> None:
    index = INDEX.read_text(encoding="utf-8")

    assert 'pages/pages-civilization.css?v=20260808-civilization13' in index
    assert 'pages/pages-civilization-mobile.css?v=20260808-mobile-app5' in index
    assert 'pages/pages-civilization-mobile.jsx?v=20260808-mobile-app5' in index
    assert 'pages/pages-civilization.jsx?v=20260808-civilization19' in index
    assert 'pages/civilization-postcard.js?v=20260808-share4' in index
    assert 'pages/pages-perms.jsx?v=20260808-civilization-preset1' in index
    assert 'app.jsx?v=20260808-civilization-app2' in index
    assert 'dist/app.bundle.js?v=20260808-civilization21' in index
    assert index.index("pages/pages-civilization-mobile.jsx") < index.index(
        "pages/pages-civilization.jsx"
    )


def test_civilization_mobile_a_reuses_the_desktop_controller_and_api_contract() -> None:
    source = PAGE.read_text(encoding="utf-8")
    mobile = MOBILE_PAGE.read_text(encoding="utf-8")
    style = MOBILE_STYLE.read_text(encoding="utf-8")

    assert "W2.CivilizationMobileA = CivilizationMobileA" in mobile
    assert 'className="civ-mobile-word"' in mobile
    assert 'className="civ-mobile-word-layer civ-mobile-word-offset is-red"' in mobile
    assert 'className="civ-mobile-word-layer civ-mobile-word-offset is-blue"' in mobile
    assert 'className="civ-mobile-word-layer civ-mobile-word-offset is-green"' in mobile
    assert "civ-mobile-color-pass 7.2s" in style
    assert "height: 7px" in style
    assert ".civilization-page.civilization-app-page" in style
    assert "min-height: 100svh" in style
    assert "env(safe-area-inset-top)" in style
    assert "env(safe-area-inset-bottom)" in style
    assert "const MobileChronology" in mobile
    assert "const MobileReader" in mobile
    assert "const MobileNotebook" in mobile
    assert "D / PERSONAL NOTEBOOK" in mobile
    assert "我的讀書筆記" in mobile
    assert "分享與長圖" in mobile
    assert "publicationStatus" in mobile
    assert 'className="civ-mobile-timeline"' in mobile
    assert 'className="civ-mobile-reader-cover"' in mobile
    assert 'className="civ-mobile-chrono-disc"' in mobile
    assert 'className="civ-mobile-chrono-frame"' in mobile
    assert 'className="civ-mobile-chrono-bar is-red"' in mobile
    assert "civ-mobile-chrono-frame 7.2s" in style
    assert "civ-mobile-chrono-disc 7.2s" in style
    assert "civ-mobile-chrono-bar 7.2s" in style
    assert "background-size: 48px 48px" in style
    assert 'data-domain={themeDomain.key}' in mobile
    assert 'style={themeDomain.style}' in mobile
    for domain in ("judgement", "technology", "organization", "time", "ethics"):
        assert f'.civ-mobile-chronology[data-domain="{domain}"]' in style
        assert f'.civ-mobile-reader[data-domain="{domain}"]' in style
    for token in (
        "--civ-theme-primary",
        "--civ-theme-secondary",
        "--civ-theme-highlight",
        "--civ-theme-ink",
        "--civ-theme-paper",
    ):
        assert token in source
        assert token in style
    assert ".civ-mobile-reading-body { color: #141414;" in style
    assert "position: fixed; left: 50%; bottom: 0" in style
    assert "width: min(480px, 100vw)" in style
    assert ".civ-mobile-only" not in style
    assert ".civ-desktop-only" not in style
    assert "W2.CivilizationMobileA" in source
    assert 'window.W2.PAGES["civilization-app"]' in source
    assert 'civilizationApp ? (MobileView ? <MobileView' in source
    assert 'civilizationApp ? " civilization-app-page" : ""' in source
    assert 'className="civ-mobile-only"' not in source
    assert 'className="civ-desktop-only"' not in source
    assert "thoughts={mobileThoughts}" in source
    assert "myNotes={mobileOwnNotes}" in source
    assert "allThoughts.filter(thought => thought.is_mine)" in source
    assert 'mode: "reading-note"' in source
    assert 'mode={composer.mode}' in source
    assert "selectedId={selected && selected.id}" in source
    assert "readerModel={mobileReader}" in source
    assert "chronology={chronology}" not in source
    assert "reader={reader}" not in source
    assert "onRetry={loadThoughts}" in source
    assert "onShare={openShare}" in source
    assert "onRead={id => selectThought(id, \"c\")}" in source
    assert "W2.json(" not in mobile
    assert "W2.post(" not in mobile
    assert 'method: "PATCH"' not in mobile
    assert 'method: "PUT"' not in mobile
    assert 'method: "DELETE"' not in mobile
    assert ".civ-mobile-notebook" in style
    assert ".civ-mobile-note-create" in style
    assert ".civ-mobile-note-list" in style


def test_civilization_app_route_inherits_the_civilization_navigation_permission() -> None:
    app = APP.read_text(encoding="utf-8")

    assert 'route === "civilization-app" ? "civilization" : route' in app
    assert "navModel.routeItems.some(n => n.id === permissionRoute)" in app


def test_public_civilization_page_and_browser_postcard_are_static_assets() -> None:
    page = PUBLIC_PAGE.read_text(encoding="utf-8")
    script = PUBLIC_SCRIPT.read_text(encoding="utf-8")
    style = PUBLIC_STYLE.read_text(encoding="utf-8")
    postcard = POSTCARD.read_text(encoding="utf-8")

    assert "__PAGE_TITLE__" in page
    assert "/pages/pages-civilization-public.css?v=20260808-share1" in page
    assert "/pages/civilization-postcard.js?v=20260808-share4" in page
    assert "/pages/pages-civilization-public.js?v=20260808-share2" in page
    assert "/api/public/civilization/" in script
    assert 'credentials:"omit"' in script
    assert "navigator.share" in script
    assert "window.CivilizationPostcard" in postcard
    assert 'document.createElement("canvas")' in postcard
    assert 'canvas.toBlob' in postcard
    assert "canvas.width = WIDTH" in postcard
    assert "const WIDTH = 1080" in postcard
    assert "downloadLong" in postcard
    assert "MAX_HEIGHT = 14000" in postcard
    assert "drawDomainGeometry(context, domainKey, palette)" in postcard
    assert 'const readingQuote = String(content.quote || "").trim()' in postcard
    assert 'quote: ""' in postcard
    assert 'type: "reading-quote"' in postcard
    assert 'type: "reading-quote-label"' in postcard
    for domain, renderer in (
        ("judgement", "drawJudgementGeometry"),
        ("technology", "drawTechnologyGeometry"),
        ("organization", "drawOrganizationGeometry"),
        ("time", "drawTimeGeometry"),
        ("ethics", "drawEthicsGeometry"),
    ):
        assert f"{domain}: {renderer}" in postcard
    assert "html2canvas" not in postcard
    assert "fetch(" not in postcard
    assert ".cp-poster" in style


def test_civilization_content_is_tenant_data_with_database_isolation() -> None:
    schema_migration = SCHEMA_MIGRATION.read_text(encoding="utf-8")
    empty_data_migration = EMPTY_DATA_MIGRATION.read_text(encoding="utf-8")
    publishing_migration = PUBLISHING_MIGRATION.read_text(encoding="utf-8")
    public_sharing_migration = PUBLIC_SHARING_MIGRATION.read_text(encoding="utf-8")
    company_preset_migration = COMPANY_PRESET_MIGRATION.read_text(encoding="utf-8")

    assert 'warehouse_scope = "schema"' in schema_migration
    assert "CREATE TABLE civilization.thoughts" in schema_migration
    assert "ENABLE ROW LEVEL SECURITY" in schema_migration
    assert "FORCE ROW LEVEL SECURITY" in schema_migration
    assert "tenant_id = app.current_tenant_id()" in schema_migration
    assert "INSERT INTO civilization.thoughts" not in schema_migration
    assert 'warehouse_scope = "primary_data"' in empty_data_migration
    assert "INSERT" not in empty_data_migration
    assert "DELETE" not in empty_data_migration
    assert "No application rows are written" in empty_data_migration
    assert 'warehouse_scope = "schema"' in publishing_migration
    assert "CREATE TABLE civilization.thought_revisions" in publishing_migration
    assert "published_content jsonb" in publishing_migration
    assert "draft_content jsonb" in publishing_migration
    assert "UPDATE civilization.thoughts" not in publishing_migration
    assert 'warehouse_scope = "schema"' in public_sharing_migration
    assert "public_share_enabled boolean NOT NULL DEFAULT false" in public_sharing_migration
    assert "CREATE TABLE civilization.public_shares" in public_sharing_migration
    assert "published_content" not in public_sharing_migration
    assert "INSERT INTO civilization.public_shares" not in public_sharing_migration
    assert "UPDATE civilization.thoughts" not in public_sharing_migration
    assert "app.current_actor_user_id()" in company_preset_migration
    assert "created_by = app.current_actor_user_id()" in company_preset_migration
    assert "'civilization'" in company_preset_migration
