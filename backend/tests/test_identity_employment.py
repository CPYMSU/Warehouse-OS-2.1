from pathlib import Path
from uuid import UUID

from app.api.deps import ActorContext
from app.api.full_stack_business import _record_visible
from app.main import app
from app.services.identity_employment import _archived_profile

ROOT = Path(__file__).parents[2]


def _actor(*, role_level: int = 3, permissions: frozenset[str] = frozenset()) -> ActorContext:
    return ActorContext(
        user_id=UUID("10000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("20000000-0000-0000-0000-000000000001"),
        tenant_slug="bonfire",
        tenant_name="Bonfire",
        industry_template_key="research_lab",
        username="researcher@example.test",
        display_name="Researcher",
        role_level=role_level,
        topology_level=role_level,
        topology_title=None,
        permissions=permissions,
    )


def test_personnel_snapshot_respects_profile_privacy_and_strips_avatar_content() -> None:
    result = _archived_profile(
        {
            "display_name": "Researcher",
            "contact": {"email": "researcher@example.test", "phone": "+1-555-0100"},
            "bio": "Research biography",
            "mbti": "INTJ",
            "avatar": {
                "kind": "upload",
                "value": "raw-image",
                "data_url": "data:image/webp;base64,secret",
                "url": "/api/account/avatar/content/example",
            },
            "privacy": {
                "email": "archive",
                "phone": "private",
                "bio": "archive",
                "mbti": "private",
                "avatar": "archive",
            },
        }
    )

    assert result["contact"] == {"email": "researcher@example.test"}
    assert result["bio"] == "Research biography"
    assert "mbti" not in result
    assert result["avatar"] == {"kind": "upload"}


def test_restricted_personnel_record_is_visible_only_to_subject_or_record_manager() -> None:
    own_record = {
        "type_key": "personnel_record",
        "subject_user_id": "10000000-0000-0000-0000-000000000001",
    }
    other_record = {
        "type_key": "personnel_record",
        "subject_user_id": "10000000-0000-0000-0000-000000000002",
    }

    assert _record_visible(_actor(), own_record) is True
    assert _record_visible(_actor(), other_record) is False
    assert _record_visible(
        _actor(permissions=frozenset({"records.all.manage"})), other_record
    ) is True


def test_employment_and_personnel_schema_is_versioned_and_tenant_isolated() -> None:
    migration = (
        ROOT
        / "backend"
        / "alembic"
        / "versions"
        / "20260802_0052_employment_personnel_records.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260802_0052"' in migration
    assert "CREATE TABLE iam.employment_profiles" in migration
    assert "CREATE TABLE records.personnel_files" in migration
    assert "CREATE TABLE records.personnel_file_versions" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "trg_membership_employment_identity" in migration


def test_employment_profile_management_contract_is_published() -> None:
    operations = app.openapi()["paths"]["/api/org/users/{user_id}/employment-profile"]
    assert "patch" in operations


def test_personal_panel_renders_database_employment_and_archive_fields() -> None:
    source = (ROOT / "frontend" / "v2" / "app.jsx").read_text(encoding="utf-8")

    for field in (
        'officialValue("employee_no", "employee_number", "staff_no")',
        'officialValue("company_name", "company")',
        'officialValue("department_name", "department")',
        'officialValue("position_name", "position", "job_title")',
        'officialValue("employment_type", "contract_type")',
        'officialValue("manager_name", "manager")',
    ):
        assert field in source
    assert "archive.record_no" in source
    assert "archive.synced_at" in source
    assert "archive.pending_count" in source
