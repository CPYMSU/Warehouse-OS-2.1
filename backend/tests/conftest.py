"""Pytest safeguards for tests that require a disposable PostgreSQL database."""

from __future__ import annotations

import os

import pytest

INTEGRATION_ENV = "WAREHOUSE_RUN_INTEGRATION_TESTS"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: exercises PostgreSQL with real tenant data; "
        "run only against a disposable database",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get(INTEGRATION_ENV) == "1":
        return

    skip_integration = pytest.mark.skip(
        reason=(
            "requires a disposable PostgreSQL database; set "
            f"{INTEGRATION_ENV}=1 to run explicitly"
        )
    )
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip_integration)
