from pathlib import Path

from app.main import app
from app.terminal.catalog import entry_by_tool_name


def test_member_and_role_commands_use_native_atomic_contracts() -> None:
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/users/create"]
    assert "post" in paths["/api/users/import"]
    assert "post" in paths["/api/roles"]
    assert "post" in paths["/api/roles/{role_ref}"]

    single = entry_by_tool_name("user_add")
    batch = entry_by_tool_name("user_import")
    role = entry_by_tool_name("role_upsert")
    assert single is not None
    assert batch is not None
    assert role is not None
    single_destinations = {item["dest"] for item in single["params"]}
    assert {
        "body.username",
        "body.password",
        "body.department",
        "body.position",
        "body.access_role",
    }.issubset(single_destinations)
    assert "body.role" not in single_destinations
    assert single["semantic_contract"]["resource"] == "iam.member"
    assert single["semantic_contract"]["access_role_policy"] == (
        "explicit_only_never_infer_from_position"
    )
    assert batch["semantic_contract"]["transaction_policy"] == "all_or_nothing"
    assert role["semantic_contract"]["canonical_identity"] == "iam.roles"
    assert single["confirmation_policy"] == {
        "mode": "passkey",
        "adapter": "staged_action",
    }


def test_iam_semantic_migration_is_registry_driven() -> None:
    migration = (
        Path(__file__).parents[1]
        / "alembic/versions/20260805_0075_iam_member_semantic_contract.py"
    ).read_text()

    assert "ADD COLUMN aliases jsonb" in migration
    assert "org:member" in migration
    assert "iam.member_directory" in migration
    assert "iam.role_directory" in migration
    assert "security_invoker=true" in migration
    assert "iam.member.provisioning_adapter" in migration
    assert "position_role_separation" in migration
    assert "password_hash" not in migration
