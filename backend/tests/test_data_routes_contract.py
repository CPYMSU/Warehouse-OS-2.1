from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.data_routes import _normalise_payload


def _route_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "route_key": "mk7-mk5-context",
        "name": "MK7 ↔ MK5",
        "state": "draft",
        "nodes": [
            {"id": "mk7", "type": "program", "label": "MK7", "x": 20, "y": 20},
            {"id": "mk5", "type": "program", "label": "MK5", "x": 250, "y": 20},
            {"id": "out", "type": "output", "label": "Result", "x": 500, "y": 20},
        ],
        "edges": [
            {"source": "mk7", "target": "out"},
            {"source": "mk5", "target": "out"},
        ],
        "rules": {"max_rows": 500, "timeout_ms": 5000},
    }
    payload.update(changes)
    return payload


def test_data_route_api_is_registered_before_the_catch_all() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    api = (root / "backend/app/api/data_routes.py").read_text()
    main = (root / "backend/app/main.py").read_text()
    assert '@router.get("/api/data-routes")' in api
    assert '@router.post("/api/data-routes"' in api
    assert '@router.put("/api/data-routes/{route_key}")' in api
    assert main.index("app.include_router(data_routes_router)") < main.index(
        '@app.api_route(\n    "/api/{path:path}"'
    )


def test_route_definition_keeps_business_data_out_of_the_control_plane() -> None:
    route = _normalise_payload(_route_payload(state="active"))
    assert route["state"] == "active"
    assert route["route_key"] == "mk7-mk5-context"
    assert route["revision"] == 1
    assert all("database_url" not in node for node in route["nodes"])


@pytest.mark.parametrize(
    "secret_field", ["password", "database_url", "access_token", "private_key"]
)
def test_route_definition_rejects_credentials(secret_field: str) -> None:
    with pytest.raises(HTTPException, match="credentials"):
        _normalise_payload(_route_payload(rules={secret_field: "must-not-be-stored"}))


def test_published_route_requires_two_programs_output_and_connections() -> None:
    with pytest.raises(HTTPException, match="two program nodes"):
        _normalise_payload(
            _route_payload(
                state="active",
                nodes=[{"id": "mk7", "type": "program", "label": "MK7", "x": 0, "y": 0}],
                edges=[],
            )
        )


def test_assets_page_exposes_route_studio_without_business_query_execution() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2] / "frontend/v2/pages/pages-assets.jsx"
    ).read_text()
    css = (Path(__file__).resolve().parents[2] / "frontend/v2/pages/pages-assets.css").read_text()
    assert 'data-testid="data-route-studio"' in source
    assert 'W2.json("/api/data-routes?limit=100"' in source
    assert "實際資料鏈路是 MK7 ↔ MK5" in source
    assert "WAREHOUSE 不保存業務查詢結果" in source
    assert ".data-route-canvas" in css
    assert ".data-route-node.type-program" in css
