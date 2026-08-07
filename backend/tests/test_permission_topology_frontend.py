from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "frontend" / "v2" / "pages" / "pages-perms.jsx"


def test_permission_topology_supports_group_and_item_controls() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "const PermissionTopology" in source
    assert 'onKeysState(keys, "selected")' in source
    assert 'onKeysState(keys, "allow")' in source
    assert 'onKeysState(keys, "deny")' in source
    assert 'onKeysState(keys, "inherit")' in source
    assert 'onKeysState([key], state === "selected" ? "clear" : "selected")' in source


def test_permission_topology_keeps_existing_write_contracts() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "onSave({ permissions: selected, enabled })" in source
    assert "onSave({ allow, deny })" in source
    assert 'mutate("/api/org/departments/" + u.id + "/permissions", body)' in source
    assert 'mutate("/api/org/users/" + userId + "/permissions", body)' in source
