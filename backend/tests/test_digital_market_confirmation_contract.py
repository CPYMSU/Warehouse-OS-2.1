from app.terminal import legacy_catalog


def test_workspace_storage_switch_uses_existing_passkey_staged_action_contract():
    entry = legacy_catalog.entry_by_tool_name("digital_market_workspace_storage_switch")

    assert entry is not None
    assert entry["writes"] is True
    assert entry["risk"] == "normal"
    assert entry["confirmation_policy"] == {
        "mode": "passkey",
        "adapter": "staged_action",
    }
    assert legacy_catalog.confirmation_contract(entry) == {
        "mode": "passkey",
        "adapter": "staged_action",
    }
    assert legacy_catalog.ai_confirmation_required(entry) is True
