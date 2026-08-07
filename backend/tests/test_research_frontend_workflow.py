from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_PAGE = ROOT / "frontend/v2/pages/pages-research.jsx"
RESEARCH_STYLE = ROOT / "frontend/v2/pages/pages-research.css"
RESEARCH_SELECTION_STYLE = ROOT / "frontend/v2/pages/pages-research-selection.css"
RESEARCH_CONTINUITY_STYLE = ROOT / "frontend/v2/pages/pages-research-continuity.css"
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
    assert "restoreResearchReadingPositionStable" in source
    assert 'window.addEventListener("pagehide", save)' in source
    assert "rememberResearchReviewState" in source
    assert "review_state" in source
    assert "W2.tenant()" in source
    assert "detailRequestSerial" in source
    assert "request !== detailRequestSerial.current" in source
    assert "setDetailBusy(Boolean(id))" in source
    assert "READING RESEARCH INDEX…" in source


def test_docx_reader_reuses_version_scoped_render_cache_across_navigation() -> None:
    source = RESEARCH_PAGE.read_text(encoding="utf-8")

    assert "RESEARCH_DOCX_CACHE_LIMIT = 4" in source
    assert "researchDocxCacheKey" in source
    assert "renderResearchDocx(entry)" in source
    assert "adoptResearchDocx(cached, root)" in source
    assert "projectsMounted" in source
    assert 'hidden={section !== "projects"}' in source


def test_manuscript_refinement_is_browser_local_recoverable_and_formally_versioned() -> None:
    source = RESEARCH_PAGE.read_text(encoding="utf-8")
    styles = RESEARCH_STYLE.read_text(encoding="utf-8")
    selection_styles = RESEARCH_SELECTION_STYLE.read_text(encoding="utf-8")
    continuity_styles = RESEARCH_CONTINUITY_STYLE.read_text(encoding="utf-8")

    assert '["refinement", "論文精修"]' in source
    assert 'data-testid="research-refinement-workspace"' in source
    assert '"w2_research_refinement:v1:"' in source
    assert 'method: "PUT"' in source
    assert 'expected_revision: revisionRef.current' in source
    assert 'base + "/submit"' in source
    assert "提交正式 DOCX 版本" in source
    assert "不啟動 Office Runtime" in source
    assert "block.type === \"image\"" in source
    assert "AuthenticatedResearchImage" in source
    assert "W2.fetch(src)" in source
    assert "URL.createObjectURL(blob)" in source
    assert "block.type === \"table_row\"" in source
    assert ".rv-refinement-grid" in styles
    assert ".rv-refinement-table-row" in styles
    assert "DOCUMENT TWIN" in source
    assert "RefinementSemanticLayer" in source
    assert "并行启动四项专业评审" in source
    assert '"neutrality", "中立化"' in source
    assert '"professional", "专业"' in source
    assert '"chief", "主 AI"' in source
    assert "RefinementEquation" in source
    assert ".rv-refinement-agent-tabs" in styles
    assert ".rv-refinement-semantic-layer" in styles
    assert "refinementSelectionFromTextarea" in source
    assert 'base + "/annotations"' in source
    assert 'selection: selection || undefined' in source
    assert "高亮标记" in source
    assert "询问主 AI" in source
    assert ".rv-refinement-selection-dock" in selection_styles
    assert ".rv-refinement-annotation-list" in selection_styles
    assert "paperScrollRef" in source
    assert "inspectorScrollRef" in source
    assert "paper_position" in source
    assert "inspector_position" in source
    assert "selection_question" in source
    assert ".rv-refinement-image-state" in continuity_styles
    assert "position:sticky" in continuity_styles
    assert "max-height:calc(100vh - 118px)" in continuity_styles
    assert "@media(max-width:680px)" in styles
