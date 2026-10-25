"""The reading edition must obey tenant, permission and file boundaries."""

import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import ActorContext, current_actor
from app.api.research_showcase import router
from app.core.config import get_settings


@pytest.fixture
def edition(tmp_path):
    actor = ActorContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="research-owner",
        tenant_name="Research owner",
        industry_template_key="research_lab",
        username="author",
        display_name="Author",
        role_level=10,
        topology_level=10,
        topology_title=None,
        permissions=frozenset({"research.read"}),
    )
    root = tmp_path / str(actor.tenant_id) / "_showcase"
    page = root / "content" / "mk77" / "derive.html"
    page.parent.mkdir(parents=True)
    page.write_text("<!doctype html><h1>Owner edition</h1>", encoding="utf-8")
    catalog = {"available": True, "documents": [], "files": {"mk77/derive.html": {}}}
    (root / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        research_repository_root=tmp_path
    )
    return app, actor, root


def test_authenticated_reader_gets_catalog_and_exact_html(edition):
    app, _, _ = edition
    client = TestClient(app)
    response = client.get("/api/research/showcase")
    assert response.status_code == 200
    assert response.json()["available"]
    assert response.headers["cache-control"] == "private, no-store"
    page = client.get("/api/research/showcase/content/mk77/derive.html")
    assert page.status_code == 200
    assert "Owner edition" in page.text
    assert page.headers["content-type"].startswith("text/html")
    assert page.headers["cache-control"] == "private, no-store"


def test_anonymous_access_is_denied(edition):
    app, _, _ = edition
    app.dependency_overrides.pop(current_actor)
    client = TestClient(app)
    for route in ["", "/content/mk77/derive.html"]:
        assert client.get("/api/research/showcase" + route).status_code == 401


def test_rank_does_not_bypass_research_permission(edition):
    app, actor, _ = edition
    app.dependency_overrides[current_actor] = lambda: replace(actor, permissions=frozenset())
    client = TestClient(app)
    assert client.get("/api/research/showcase").status_code == 403
    assert client.get("/api/research/showcase/content/mk77/derive.html").status_code == 403


def test_other_tenant_cannot_read_the_owners_edition(edition):
    app, actor, _ = edition
    app.dependency_overrides[current_actor] = lambda: replace(actor, tenant_id=uuid4())
    client = TestClient(app)
    assert client.get("/api/research/showcase").json()["available"] is False
    assert client.get("/api/research/showcase/content/mk77/derive.html").status_code == 404


@pytest.mark.parametrize(
    "path",
    ["catalog.json", "mk77/missing.html", "..%2Fcatalog.json", "%5Ccatalog.json", "%2Fetc/passwd"],
)
def test_unlisted_or_traversing_paths_are_denied(edition, path):
    app, _, _ = edition
    assert TestClient(app).get("/api/research/showcase/content/" + path).status_code == 404


def test_manifest_cannot_allow_a_symlink_outside_content(edition, tmp_path):
    app, _, root = edition
    outside = tmp_path / "private.txt"
    outside.write_text("private", encoding="utf-8")
    link = root / "content" / "escape.html"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks requires platform privileges")
    (root / "catalog.json").write_text(json.dumps({"files": {"escape.html": {}}}), encoding="utf-8")
    assert TestClient(app).get("/api/research/showcase/content/escape.html").status_code == 404
