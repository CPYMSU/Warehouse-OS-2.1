from app.templates.industry_blueprints import (
    INDUSTRY_BLUEPRINT_KEYS,
    assert_valid_blueprints,
    get_blueprint,
    list_blueprints,
)


def test_all_thirteen_legacy_blueprints_are_available() -> None:
    assert_valid_blueprints()

    templates = list_blueprints()
    assert len(templates) == 13
    assert tuple(template["key"] for template in templates) == INDUSTRY_BLUEPRINT_KEYS


def test_power_grid_blueprint_is_renamed_to_power_system() -> None:
    assert "power_grid_uhv" not in INDUSTRY_BLUEPRINT_KEYS
    template = get_blueprint("power_system")

    assert template["name"] == "電力系統"
    assert template["admin_position_code"] == "grid_system_admin"
    assert len(template["departments"]) == 10
    assert len(template["positions"]) == 20
