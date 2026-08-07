from pathlib import Path

from app.services.organization import NAV_PERMISSION_RULES, NAVIGATION_CATALOG
from app.templates.industry_blueprints import nav_modules_for_permissions

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization.jsx"
STYLE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization.css"
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


def test_civilization_navigation_sits_between_records_and_settings() -> None:
    ids = [str(item["id"]) for item in NAVIGATION_CATALOG]

    assert ids.index("cases") < ids.index("civilization") < ids.index("settings")
    assert NAV_PERMISSION_RULES["civilization"] == ("overview.read",)
    assert "civilization" in nav_modules_for_permissions({"overview.read"})


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
    assert "CivilizationPostcard.download" in source
    assert "civ-share-card" in source
    assert ".civ-reader.is-notes-collapsed" in style
    assert "civ-lens-editor" in source
    assert "civ-poster-index" in source
    assert "12 COLUMN SYSTEM" in source
    assert "BUILTIN_THOUGHTS" not in source
    assert "const drafts" not in source
    assert ".civ-atlas-layout" in style
    assert ".civ-chronology" in style
    assert ".civ-reader" in style
    assert "civ-poster-motion" in source
    assert "data-domain" in source
    for domain in ("judgement", "technology", "organization", "time", "ethics"):
        assert f".civ-poster-motion.is-{domain}" in style
    assert "civ-poster-opposition" not in style
    assert ".civ-poster-motion { display: none; }" in style
    assert "@media (prefers-reduced-motion: reduce)" in style


def test_civilization_assets_are_in_the_production_manifest() -> None:
    index = INDEX.read_text(encoding="utf-8")

    assert 'pages/pages-civilization.css?v=20260808-civilization8' in index
    assert 'pages/pages-civilization.jsx?v=20260808-civilization8' in index
    assert 'pages/civilization-postcard.js?v=20260808-share1' in index
    assert 'dist/app.bundle.js?v=20260808-civilization8' in index


def test_public_civilization_page_and_browser_postcard_are_static_assets() -> None:
    page = PUBLIC_PAGE.read_text(encoding="utf-8")
    script = PUBLIC_SCRIPT.read_text(encoding="utf-8")
    style = PUBLIC_STYLE.read_text(encoding="utf-8")
    postcard = POSTCARD.read_text(encoding="utf-8")

    assert "__PAGE_TITLE__" in page
    assert "/pages/pages-civilization-public.css?v=20260808-share1" in page
    assert "/pages/civilization-postcard.js?v=20260808-share1" in page
    assert "/api/public/civilization/" in script
    assert 'credentials:"omit"' in script
    assert "navigator.share" in script
    assert "window.CivilizationPostcard" in postcard
    assert 'document.createElement("canvas")' in postcard
    assert 'canvas.toBlob' in postcard
    assert "html2canvas" not in postcard
    assert "fetch(" not in postcard
    assert ".cp-poster" in style


def test_civilization_content_is_tenant_data_with_database_isolation() -> None:
    schema_migration = SCHEMA_MIGRATION.read_text(encoding="utf-8")
    empty_data_migration = EMPTY_DATA_MIGRATION.read_text(encoding="utf-8")
    publishing_migration = PUBLISHING_MIGRATION.read_text(encoding="utf-8")
    public_sharing_migration = PUBLIC_SHARING_MIGRATION.read_text(encoding="utf-8")

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
