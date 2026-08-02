from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "frontend" / "v2" / "design-lab" / "digital-custody"


def test_digital_custody_lab_compares_four_inline_register_components():
    index = (LAB / "index.html").read_text(encoding="utf-8")
    assert "ONLY THE REGISTER MODULE" in index
    assert "正式頁面沒有修改" in index
    for option, module in (
        ("a", "module-a"),
        ("b", "module-b"),
        ("c", "module-c"),
        ("d", "module-d"),
    ):
        assert f'id="option-{option}"' in index
        assert f'class="asset-module {module}"' in index
    assert index.count("DMA-20260801-8A73DE5C") == 4
    assert 'name="viewport"' in index


def test_design_lab_is_static_responsive_and_does_not_modify_the_live_page():
    base = (LAB / "base.css").read_text(encoding="utf-8")
    demos = (LAB / "demos.css").read_text(encoding="utf-8")
    components = (LAB / "component-demos.css").read_text(encoding="utf-8")
    assert "@media (max-width: 880px)" in base
    assert "@media (max-width: 560px)" in base
    assert "@media (max-width: 760px)" in demos
    assert "@media (max-width: 760px)" in components
    assert "@media (max-width: 480px)" in components
    assert not list(LAB.glob("*.js"))
    live_page = (
        ROOT / "frontend" / "v2" / "pages" / "pages-assets.jsx"
    ).read_text(encoding="utf-8")
    assert "design-lab/digital-custody" not in live_page
