from pathlib import Path

from app.services.organization import NAV_PERMISSION_RULES, NAVIGATION_CATALOG
from app.templates.industry_blueprints import nav_modules_for_permissions

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization.jsx"
STYLE = ROOT / "frontend" / "v2" / "pages" / "pages-civilization.css"
INDEX = ROOT / "frontend" / "v2" / "index.html"
SCHEMA_MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "20260807_0083_civilization_thoughts.py"
)
SEED_MIGRATION = ROOT / "backend" / "alembic" / "versions" / "20260807_0084_civilization_seed.py"


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
    assert "BUILTIN_THOUGHTS" not in source
    assert "drafts" not in source
    assert ".civ-atlas-layout" in style
    assert ".civ-chronology" in style
    assert ".civ-reader" in style


def test_civilization_assets_are_in_the_production_manifest() -> None:
    index = INDEX.read_text(encoding="utf-8")

    assert 'pages/pages-civilization.css?v=20260807-civilization2' in index
    assert 'pages/pages-civilization.jsx?v=20260807-civilization2' in index
    assert 'dist/app.bundle.js?v=20260807-civilization2' in index


def test_civilization_content_is_tenant_data_with_database_isolation() -> None:
    schema_migration = SCHEMA_MIGRATION.read_text(encoding="utf-8")
    seed_migration = SEED_MIGRATION.read_text(encoding="utf-8")

    assert 'warehouse_scope = "schema"' in schema_migration
    assert "CREATE TABLE civilization.thoughts" in schema_migration
    assert "ENABLE ROW LEVEL SECURITY" in schema_migration
    assert "FORCE ROW LEVEL SECURITY" in schema_migration
    assert "tenant_id = app.current_tenant_id()" in schema_migration
    assert "INSERT INTO civilization.thoughts" not in schema_migration
    assert 'warehouse_scope = "primary_data"' in seed_migration
    assert "ON CONFLICT (tenant_id, stable_key) DO NOTHING" in seed_migration
