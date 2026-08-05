from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_PAGE = ROOT / "frontend/v2/pages/pages-research.jsx"
RESEARCH_STYLE = ROOT / "frontend/v2/pages/pages-research.css"
INDEX_HTML = ROOT / "frontend/v2/index.html"


def test_research_page_guides_paper_construction_through_real_capabilities() -> None:
    source = RESEARCH_PAGE.read_text(encoding="utf-8")

    assert '["guide", "論文導引"]' in source
    assert "RESEARCH COMPASS / NINE GATES" in source
    assert 'data-testid="research-guide-paper-selector"' in source
    assert "SELECT PAPER / 選擇論文" in source
    assert 'onChange={event => selectProject(clean(event.target.value))}' in source
    assert "切換後，九道關卡、完成度與下一步都會依這篇論文的真實資料重新計算" in source
    assert "FRAME THE QUESTION" in source
    assert "WRITE THE ARGUMENT" in source
    assert "LINK CLAIMS" in source
    assert "research dmp update" in source
    assert "research execution submit" in source
    assert "research review submit" in source
    assert "research release create" in source


def test_run_composer_exposes_actual_version_selection_contract() -> None:
    source = RESEARCH_PAGE.read_text(encoding="utf-8")

    assert "RUN COMPOSER" in source
    assert "PIN INPUT VERSIONS" in source
    assert 'executionPinMode === "custom"' in source
    assert "payload.input_file_version_ids" in source
    assert "entrypointVersionId" in source
    assert "NO INTERNET" in source
    assert "READ-ONLY INPUTS" in source


def test_research_guide_and_run_composer_have_responsive_swiss_layouts() -> None:
    styles = RESEARCH_STYLE.read_text(encoding="utf-8")

    for selector in (
        ".rv-guide-poster",
        ".rv-guide-binding",
        ".rv-journey-grid",
        ".rv-paper-spine",
        ".rv-run-composer",
        ".rv-run-input-list",
        ".rv-run-preflight",
    ):
        assert selector in styles
    assert "@media(max-width:820px)" in styles
    assert "@media(max-width:520px)" in styles


def test_object_register_exposes_swiss_research_asset_topology() -> None:
    source = RESEARCH_PAGE.read_text(encoding="utf-8")
    styles = RESEARCH_STYLE.read_text(encoding="utf-8")

    assert 'data-testid="research-object-topology"' in source
    assert "SWISS OBJECT TOPOLOGY" in source
    assert '["manuscript", "PAPER", "論文"]' in source
    assert '["code", "CODE", "代碼"]' in source
    assert '["dataset", "DATA", "數據"]' in source
    assert "visibleResearchFiles.map" in source
    assert ".rv-object-topology" in styles
    assert ".rv-asset-class" in styles


def test_paper_review_exposes_faithful_word_selection_annotations_and_grounded_ai() -> None:
    source = RESEARCH_PAGE.read_text(encoding="utf-8")
    styles = RESEARCH_STYLE.read_text(encoding="utf-8")
    index = INDEX_HTML.read_text(encoding="utf-8")

    assert "VERSION-PINNED PAPER REVIEW" in source
    assert "capturePaperSelection" in source
    assert 'base + "/annotations"' in source
    assert 'base + "/questions"' in source
    assert "每個答案回指版本固定的段落與字符位置" in source
    assert "window.docx.renderAsync" in source
    assert "renderFootnotes: true" in source
    assert "renderEndnotes: true" in source
    assert "docx-preview.min.js?v=0.3.6" in index
    assert "jszip.min.js?v=3.10.1" in index
    assert ".rv-review-workspace" in styles
    assert "::highlight(research-review-focus)" in styles


def test_research_index_restores_last_project_file_tab_and_reading_position() -> None:
    source = RESEARCH_PAGE.read_text(encoding="utf-8")

    assert '"w2_research_memory:v1:"' in source
    assert "rememberedResearchProject()" in source
    assert "rememberedResearchFile(id)" in source
    assert "rememberedResearchTab(id, selected, fallbackTab)" in source
    assert "saveResearchReadingPosition" in source
    assert "restoreResearchReadingPosition" in source
    assert "W2.tenant()" in source


def test_docx_reader_reuses_version_scoped_render_cache_across_navigation() -> None:
    source = RESEARCH_PAGE.read_text(encoding="utf-8")

    assert "RESEARCH_DOCX_CACHE_LIMIT = 4" in source
    assert "researchDocxCacheKey" in source
    assert "renderResearchDocx(entry)" in source
    assert "adoptResearchDocx(cached, root)" in source
    assert "projectsMounted" in source
    assert 'hidden={section !== "projects"}' in source
