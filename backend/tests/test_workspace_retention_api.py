"""API contract for explicit release selection before destructive retention."""

from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import workspace_autonomy as api
from app.core.config import get_settings


def test_retention_query_preserves_explicit_deployment_selection(monkeypatch):
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.autonomous_workspace_credential] = lambda: object()
    app.dependency_overrides[get_settings] = lambda: object()
    observed = []
    monkeypatch.setattr(
        api, "plan_workspace_retention",
        lambda credential, settings, payload: observed.append(payload) or {"ok": True},
    )
    ids = [str(uuid4()), str(uuid4())]
    client = TestClient(app)
    response = client.get(
        "/api/workspaces/v1/retention/plan",
        params=[*(('deployment_ids', item) for item in ids),
                ('include_sources', 'false'), ('include_expired_uploads', 'false'),
                ('include_python_environments', 'true')],
    )
    assert response.status_code == 200
    assert observed[-1]["deployment_ids"] == ids
    assert observed[-1]["include_sources"] is False
    assert observed[-1]["include_expired_uploads"] is False
    assert observed[-1]["include_python_environments"] is True
    assert client.get('/api/workspaces/v1/retention/plan').status_code == 200
    assert observed[-1]["deployment_ids"] is None
    assert observed[-1]["include_sources"] is True
    assert observed[-1]["include_expired_uploads"] is True
    count = len(observed)
    assert client.get(
        '/api/workspaces/v1/retention/plan',
        params=[('deployment_ids', str(uuid4())) for _ in range(201)],
    ).status_code == 422
    assert len(observed) == count
