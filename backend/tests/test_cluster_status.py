from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import cluster_status
from app.main import app


def test_cluster_identity_exposes_release_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv("WAREHOUSE_NODE_ID", "mac-primary")
    monkeypatch.setenv("WAREHOUSE_NODE_ROLE", "primary")
    monkeypatch.setenv("WAREHOUSE_RELEASE_ID", "release-123")
    monkeypatch.setenv("WAREHOUSE_GIT_SHA", "abc123")
    monkeypatch.setenv("WAREHOUSE_ALEMBIC_HEAD", "0069")
    monkeypatch.setenv("WAREHOUSE_NODE_PLATFORM", "linux/arm64")
    monkeypatch.setenv("WAREHOUSE_CLUSTER_PEERS", "vultr-standby")

    response = TestClient(app).get("/api/system/cluster")

    assert response.status_code == 200
    assert response.json() == {
        "schema": "warehouse.cluster-node.v1",
        "node_id": "mac-primary",
        "node_role": "primary",
        "release_id": "release-123",
        "git_sha": "abc123",
        "alembic_head": "0069",
        "platform": "linux/arm64",
        "peers": ["vultr-standby"],
    }


def test_cluster_readiness_rejects_database_failure(monkeypatch) -> None:
    monkeypatch.setattr(cluster_status, "database_is_available", lambda: False)

    response = TestClient(app).get("/api/system/readiness")

    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "unavailable"
