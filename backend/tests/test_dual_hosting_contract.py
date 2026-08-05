from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.hosting_modes import (
    TERMINAL_WORKSPACE_RUNTIME_STATUS,
    _hosting_settings,
    _terminal_workspace_state,
    hosting_public,
)
from app.services.intelligent_hosting import (
    TERMINAL_SESSION_READY_EVENT,
    _merge_desired_state,
    assistant_manifest,
)


def _workspace(**overrides: object) -> dict[str, object]:
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "tenant_id": "00000000-0000-0000-0000-000000000002",
        "asset_id": "00000000-0000-0000-0000-000000000003",
        "hosting_mode": "cloud",
        "compute_node": "warehouse",
        "config": {},
        **overrides,
    }


def test_cloud_is_the_backward_compatible_default() -> None:
    settings = _hosting_settings({}, _workspace())
    assert settings["hosting_mode"] == "cloud"
    assert settings["compute_node"] == "warehouse"
    assert hosting_public(_workspace())["cloud_compute_billable"] is True


def test_terminal_mode_is_explicit_and_uses_the_user_terminal() -> None:
    settings = _hosting_settings(
        {
            "mode": "terminal",
            "notify_targets": ["terminal", "ai"],
            "cloud_fallback": "ask",
        },
        _workspace(),
    )
    assert settings["hosting_mode"] == "terminal"
    assert settings["compute_node"] == "user_terminal"
    assert settings["notify_targets"] == ["terminal", "ai"]


def test_terminal_mode_rejects_a_cloud_compute_node() -> None:
    with pytest.raises(HTTPException, match="terminal hosting"):
        _hosting_settings(
            {"mode": "terminal", "compute_node": "mac_mini"},
            _workspace(),
        )


def test_switching_back_to_cloud_does_not_keep_user_terminal_as_node() -> None:
    settings = _hosting_settings(
        {"mode": "cloud"},
        _workspace(hosting_mode="terminal", compute_node="user_terminal"),
    )
    assert settings["hosting_mode"] == "cloud"
    assert settings["compute_node"] == "warehouse"


def test_ai_desired_state_can_select_hosting_mode() -> None:
    merged = _merge_desired_state(
        {},
        {"hosting": {"mode": "terminal", "notify_targets": ["ai"]}},
    )
    assert merged["hosting"]["mode"] == "terminal"


def test_ai_desired_state_rejects_unknown_hosting_mode() -> None:
    with pytest.raises(HTTPException, match="hosting.mode"):
        _merge_desired_state({}, {"hosting": {"mode": "p2p"}})


def test_manifest_publishes_terminal_and_notification_contract() -> None:
    manifest = assistant_manifest()
    assert manifest["desired_state"]["hosting"]["mode"] == (
        "cloud|terminal; user-selected execution location"
    )
    assert manifest["conversation"]["notifications"] == (
        "GET /api/hosting/v2/notifications?workspace_ref=..."
    )
    assert manifest["conversation"]["compute_usage"] == (
        "GET /api/hosting/v2/compute-usage?workspace_ref=..."
    )
    assert manifest["conversation"]["terminal_manifest"].startswith(
        "GET /api/hosting/v2/terminal-actions/"
    )
    assert manifest["conversation"]["terminal_complete"].startswith(
        "POST /api/hosting/v2/terminal-actions/"
    )


def test_terminal_session_completion_uses_existing_ready_event_contract() -> None:
    """Terminal readiness is carried by the stage/payload, not a new DB event value."""

    assert TERMINAL_SESSION_READY_EVENT == "ready"


def test_terminal_completion_does_not_claim_server_runtime_ready() -> None:
    state = _terminal_workspace_state(
        "00000000-0000-0000-0000-000000000004",
        True,
    )

    assert state["runtime_status"] == TERMINAL_WORKSPACE_RUNTIME_STATUS == "provisioned"
    assert state["config"]["terminal_last_status"] == "succeeded"
    assert state["config"]["terminal_last_deployment_id"].endswith("0004")
