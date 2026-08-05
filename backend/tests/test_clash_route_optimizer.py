from __future__ import annotations

import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "ops"
    / "macos"
    / "warehouse-clash-route-optimizer"
)
MODULE = runpy.run_path(str(SCRIPT))
choose_route: Callable[
    [str, dict[str, int], dict[str, Any]], tuple[str, str, int]
] = MODULE["choose_route"]
singapore_name: Callable[[str], bool] = MODULE["singapore_name"]


def test_clash_optimizer_recognizes_only_singapore_route_names() -> None:
    assert singapore_name("🇸🇬 [精品/5x] SG")
    assert singapore_name("Relay SG 2")
    assert not singapore_name("🇯🇵 [中转] JP 1")


def test_clash_optimizer_keeps_current_route_inside_hysteresis() -> None:
    selected, reason, streak = choose_route(
        "SG current",
        {"SG current": 110, "SG candidate": 100},
        {},
    )

    assert (selected, reason, streak) == ("SG current", "within_hysteresis", 0)


def test_clash_optimizer_requires_two_confirmations_for_a_faster_route() -> None:
    delays = {"SG current": 145, "SG candidate": 100}

    first = choose_route("SG current", delays, {})
    second = choose_route(
        "SG current",
        delays,
        {"pending": "SG candidate", "pending_streak": 1},
    )

    assert first == ("SG current", "awaiting_confirmation", 1)
    assert second == ("SG candidate", "confirmed_faster", 2)


def test_clash_optimizer_immediately_replaces_an_unhealthy_route() -> None:
    selected, reason, streak = choose_route(
        "SG failed",
        {"SG failed": 0, "SG healthy": 108},
        {},
    )

    assert (selected, reason, streak) == ("SG healthy", "current_unhealthy", 0)
