from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "docs" / "design-references" / "swiss"


def test_swiss_reference_library_keeps_sources_and_licenses_together():
    required = (
        "README.md",
        "UPSTREAM.lock.md",
        "ATTRIBUTION.md",
        "upstream/raster/LICENSE.txt",
        "upstream/raster/raster.grid.css",
        "upstream/raster/examples/poster.html",
        "upstream/swiss-confederation/LICENSE",
        "upstream/swiss-confederation/css/foundations/colors.postcss",
        "upstream/swiss-confederation/css/layouts/grids.postcss",
        "upstream/swiss-post/LICENSE",
        "upstream/swiss-post/packages/styles/src/components/tables.scss",
        "upstream/swiss-post/packages/styles/src/components/tabs/index.scss",
    )
    for relative_path in required:
        assert (LIBRARY / relative_path).is_file(), relative_path

    lock = (LIBRARY / "UPSTREAM.lock.md").read_text(encoding="utf-8")
    assert "https://github.com/swiss/designsystem" in lock
    assert "5f03f257b64d459e689c24d309c508a7af4771ae" in lock
    assert "https://github.com/swisspost/design-system" in lock
    assert "27c1cd52ef1345b0e8db4caf92e217eb6aebcd44" in lock
    assert "https://github.com/rsms/raster" in lock
    assert "b28022f4f3570d09a3f264f5b7fa6d250d75bbc4" in lock
    assert "MIT" in lock
    assert "Apache-2.0" in lock


def test_original_swiss_studies_cover_register_data_type_and_actions():
    index = (LIBRARY / "studies" / "index.html").read_text(encoding="utf-8")
    css = (LIBRARY / "studies" / "studies.css").read_text(encoding="utf-8")
    for study in ("study-01", "study-02", "study-03", "study-04"):
        assert f'id="{study}"' in index
    assert "RESTRAINED REGISTER" in index
    assert "ASYMMETRIC DATA POSTER" in index
    assert "TYPOGRAPHIC INDEX" in index
    assert "ACTION HIERARCHY" in index
    assert "NOT A HISTORICAL POSTER REPRODUCTION" in index
    assert "@media(max-width:800px)" in css
    assert "@media(max-width:480px)" in css


def test_reference_code_remains_documentation_only_and_excludes_binary_brand_assets():
    app_index = (ROOT / "frontend" / "v2" / "index.html").read_text(encoding="utf-8")
    assert "design-references/swiss" not in app_index
    disallowed_suffixes = {".woff", ".woff2", ".ttf", ".otf", ".png", ".jpg", ".jpeg", ".gif"}
    assert not [path for path in LIBRARY.rglob("*") if path.suffix.lower() in disallowed_suffixes]
