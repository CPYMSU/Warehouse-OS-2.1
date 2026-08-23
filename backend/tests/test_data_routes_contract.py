from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.data_routes import _code_route_manifests, _normalise_payload


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
        "source": {
            "kind": "route_manifest",
            "repository": "warehouse://programs/mk7",
            "ref": "main@c24774c",
            "path": "routes/mk7-mk5.yaml",
            "digest": "sha256:route-manifest",
            "parser": "warehouse-route-manifest/v1",
            "observed_at": "2026-08-23T12:00:00+00:00",
        },
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
    assert route["source_of_truth"] == "program_code"
    assert route["editable_in_warehouse"] is False
    assert route["source"]["path"] == "routes/mk7-mk5.yaml"
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


def test_bonfire_code_manifest_declares_safe_three_program_route() -> None:
    routes = _code_route_manifests("bonfire")
    route = next(item for item in routes if item["route_key"] == "mk7-tidi-mk4-federated-search")
    program_ids = {node["id"] for node in route["nodes"] if node["type"] == "program"}
    rules = route["rules"]
    assert program_ids == {"mk7", "tidi", "mk4"}
    assert route["state"] == "suspended"
    assert route["code_managed"] is True
    assert route["editable_in_warehouse"] is False
    assert rules["database_direct_access"] == "forbidden"
    assert rules["database_schema_change"] == "none"
    assert rules["write_mode"] == "deny"
    assert rules["activation_gate"]["display_label"] == "等待端点授权"
    assert "candidate_fact" in rules["source_policies"]["mk5_tidi"]["deny"]
    assert "published_fact_after_completed_second_review" in (
        rules["source_policies"]["mk5_tidi"]["allow_after_gate"]
    )


def test_code_manifest_is_tenant_scoped() -> None:
    assert not _code_route_manifests("another-company")


def test_assets_page_exposes_read_only_code_route_topology() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2] / "frontend/v2/pages/pages-assets.jsx"
    ).read_text()
    css = (Path(__file__).resolve().parents[2] / "frontend/v2/pages/pages-assets.css").read_text()
    assert 'data-testid="data-route-observer"' in source
    assert "<DataRouteObserver/>" in source
    assert "<DataRouteStudioEditor" not in source
    assert 'W2.json("/api/data-routes?limit=100"' in source
    assert "不在此頁建立、連線或修改路由" in source
    assert "CODE IS SOURCE OF TRUTH" in source
    assert "WAREHOUSE EDITABLE <b>NO</b>" in source
    assert "Route Gate" in source
    assert "activation_gate" in source
    assert ".data-route-canvas" in css
    assert ".data-route-canvas.is-readonly" in css
    assert ".data-route-node.type-program" in css
