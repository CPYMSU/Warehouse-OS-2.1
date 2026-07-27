from fastapi.testclient import TestClient

from app.main import app


def test_liveness_endpoint_does_not_need_a_database_connection() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "warehouse-os-api"}
