from pathlib import Path
from uuid import UUID

from app.api.deps import ActorContext
from app.services.identity_titles import compose_official_titles


def _actor() -> ActorContext:
    return ActorContext(
        user_id=UUID("10000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("20000000-0000-0000-0000-000000000001"),
        tenant_slug="bonfire",
        tenant_name="Bonfire",
        industry_template_key="research_lab",
        username="researcher@example.test",
        display_name="Researcher",
        role_level=10,
        topology_level=10,
        topology_title="系統管理員",
    )


def _definitions() -> list[dict[str, object]]:
    return [
        {
            "code": "professor",
            "category": "academic_appointment",
            "label_zh_hant": "教授",
            "label_zh_hans": "教授",
            "label_en": "Professor",
            "abbreviation": "Prof.",
            "priority": 10,
            "name_prefix": True,
        },
        {
            "code": "doctor",
            "category": "academic_degree",
            "label_zh_hant": "博士",
            "label_zh_hans": "博士",
            "label_en": "Doctor",
            "abbreviation": "Dr.",
            "priority": 20,
            "name_prefix": True,
        },
        {
            "code": "ceo",
            "category": "organizational_office",
            "label_zh_hant": "首席執行官",
            "label_zh_hans": "首席执行官",
            "label_en": "Chief Executive Officer",
            "abbreviation": "CEO",
            "priority": 50,
            "name_prefix": False,
        },
    ]


def test_verified_academic_titles_precede_public_offices() -> None:
    result = compose_official_titles(
        _actor(),
        definitions=_definitions(),
        claims=[
            {
                "title_code": "doctor",
                "source_kind": "verified_record",
                "source_ref": "degree-record-01",
            }
        ],
        positions=[
            {
                "position_code": "visiting_professor",
                "name": "兼職教授",
                "name_en": "Visiting Professor",
                "role_name": "Professor",
                "role_level": 6,
                "is_manager": False,
                "title_code": "professor",
                "appointment_type": "concurrent",
            },
            {
                "position_code": "scientific_research_center_director",
                "name": "科研中心主任",
                "name_en": "Research Centre Director",
                "role_name": "Director",
                "role_level": 10,
                "is_manager": True,
                "title_code": None,
                "appointment_type": "primary",
            },
            {
                "position_code": "lab_system_admin",
                "name": "系統管理員",
                "name_en": "System Administrator",
                "role_name": "Administrator",
                "role_level": 10,
                "is_manager": True,
                "title_code": None,
                "appointment_type": "concurrent",
            },
        ],
    )

    assert result["title_prefix"] == "Prof. Dr."
    assert result["primary_title"]["code"] == "professor"
    assert result["primary_office"]["code"] == "office:scientific_research_center_director"
    assert [item["rank"] for item in result["titles"]] == [1, 2, 3]
    assert [item["code"] for item in result["titles"]] == [
        "professor",
        "doctor",
        "office:scientific_research_center_director",
    ]
    assert result["highest_education"] == "doctorate"
    assert result["title_source"]["permissions_unchanged"] is True


def test_standard_office_title_can_be_the_primary_title() -> None:
    result = compose_official_titles(
        _actor(),
        definitions=_definitions(),
        claims=[],
        positions=[
            {
                "position_code": "ceo",
                "name": "首席執行官",
                "name_en": "Chief Executive Officer",
                "role_name": "Executive",
                "role_level": 10,
                "is_manager": True,
                "title_code": "ceo",
                "appointment_type": "primary",
            }
        ],
    )

    assert result["title_prefix"] == ""
    assert result["primary_title"]["display"] == "CEO"
    assert result["primary_office"]["code"] == "ceo"
    assert result["titles"][0]["verified"] is True


def test_frontend_masthead_uses_profile_avatar_and_primary_rank() -> None:
    source = (Path(__file__).parents[2] / "frontend" / "v2" / "app.jsx").read_text(
        encoding="utf-8"
    )

    assert 'W2.json("/api/account/profile")' in source
    assert '<PersonalAvatar avatar={accountAvatar}' in source
    assert 'className="mast-account-rank"' in source
    assert "accountTitles[0]" in source
