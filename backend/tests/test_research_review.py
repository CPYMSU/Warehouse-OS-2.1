from __future__ import annotations

import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api import research as research_api
from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import system_session
from app.main import app
from app.services import research_review
from app.services.integrations import ModelConnection
from app.services.research_review import parse_document_blocks, resolve_anchor


def _paper_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "word/styles.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/></w:style>
              <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="Heading 1"/></w:style>
            </w:styles>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document
              xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
              xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
              xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
              <w:body>
                <w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>MK51 Paper</w:t></w:r></w:p>
                <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Method</w:t></w:r></w:p>
                <w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Calibrated response</w:t></w:r>
                  <w:r><w:drawing><wp:docPr id="1" name="Figure 1"
                    descr="Calibration curve"/></w:drawing></w:r>
                </w:p>
                <w:p><m:oMath><m:f><m:num><m:r><m:t>a</m:t></m:r></m:num><m:den><m:r><m:t>b</m:t></m:r></m:den></m:f></m:oMath></w:p>
                <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Sample</w:t></w:r></w:p></w:tc>
                  <w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
              </w:body>
            </w:document>""",
        )


def test_docx_review_parser_preserves_structure_math_images_and_tables(tmp_path: Path) -> None:
    path = tmp_path / "paper.docx"
    _paper_docx(path)

    blocks = parse_document_blocks(
        path,
        {
            "original_filename": "paper.docx",
            "content_type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            "size_bytes": path.stat().st_size,
        },
    )

    assert [block.block_type for block in blocks] == [
        "title",
        "heading",
        "paragraph",
        "equation",
        "table_row",
    ]
    assert blocks[2].heading_path == ("MK51 Paper", "Method")
    assert "Calibrated response" in blocks[2].content
    assert "圖：Calibration curve" in blocks[2].content
    assert blocks[3].content == "ab"
    assert blocks[4].content == "Sample | Value"
    assert blocks[1].start_offset == len("MK51 Paper") + 2
    assert blocks[-1].end_offset > blocks[-1].start_offset


def test_character_anchor_uses_context_to_disambiguate_duplicate_text() -> None:
    blocks = [
        {
            "id": "one",
            "ordinal": 0,
            "content": "Alpha repeats concept here.",
            "start_offset": 0,
            "end_offset": 27,
        },
        {
            "id": "two",
            "ordinal": 1,
            "content": "Beta repeats concept there.",
            "start_offset": 29,
            "end_offset": 56,
        },
    ]

    anchor = resolve_anchor(
        blocks,
        {"quote": "repeats concept", "prefix": "Beta ", "suffix": " there."},
    )

    assert anchor["state"] == "exact"
    assert anchor["start_block_id"] == "two"
    assert anchor["start_block_ordinal"] == 1
    assert anchor["quote"] == "repeats concept"
    assert len(anchor["anchor_sha256"]) == 64


@pytest.mark.integration
def test_document_review_annotation_and_grounded_question_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    tenant_slug = f"paper-review-{tenant_id.hex[:10]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, 'Paper Review Test', 'research_lab')
                """
            ),
            {"id": tenant_id, "slug": tenant_slug},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, 'Paper Reviewer', :password_hash)
                """
            ),
            {
                "id": user_id,
                "username": f"reviewer-{user_id.hex[:10]}",
                "password_hash": hash_password("paper-review-test"),
            },
        )
    actor = ActorContext(
        user_id=user_id,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        tenant_name="Paper Review Test",
        industry_template_key="research_lab",
        username=f"reviewer-{user_id.hex[:10]}",
        display_name="Paper Reviewer",
        role_level=10,
        topology_level=10,
        topology_title="Research Director",
        permissions=frozenset({"research.read", "research.write", "research.review"}),
    )
    settings = Settings(
        asset_storage_root=tmp_path / "objects",
        research_repository_root=tmp_path / "repositories",
    )
    paper = tmp_path / "paper.docx"
    _paper_docx(paper)
    monkeypatch.setattr(research_api, "distill_document_index", lambda *args: {})
    monkeypatch.setattr(
        research_review,
        "connected_deepseek",
        lambda *_args: ModelConnection(
            base_url="https://model.invalid",
            model="test-research-model",
            api_key="test-only",
        ),
    )
    monkeypatch.setattr(
        research_review,
        "chat_completion",
        lambda *_args, **_kwargs: (
            '{"answer":"It is the calibrated experimental response.",'
            '"citations":[{"block":"B0002","quote":"Calibrated response"}]}'
        ),
    )
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        project_response = client.post(
            "/api/research/projects",
            json={"title": "Reviewable Paper", "slug": "reviewable-paper"},
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["project"]["id"]
        upload_response = client.post(
            f"/api/research/projects/{project_id}/files",
            files={
                "file": (
                    "paper.docx",
                    paper.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={"logical_path": "manuscript/paper.docx"},
        )
        assert upload_response.status_code == 201
        uploaded = upload_response.json()
        file_id = uploaded["file"]["id"]

        workspace_response = client.get(
            f"/api/research/projects/{project_id}/files/{file_id}/review"
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()
        assert workspace["index"]["status"] == "ready"
        assert workspace["index"]["block_count"] == 5
        assert workspace["capabilities"]["character_anchors"] is True
        assert workspace["version"]["filename"] == "paper.docx"
        assert "object_key" not in workspace["version"]
        assert "storage_provider" not in workspace["version"]

        annotation_response = client.post(
            f"/api/research/projects/{project_id}/files/{file_id}/annotations",
            json={
                "version": 1,
                "anchor": {"quote": "Calibrated response"},
                "body": "Confirm the calibration procedure and uncertainty.",
            },
        )
        assert annotation_response.status_code == 201
        assert annotation_response.json()["annotation"]["anchor"]["start_block_ordinal"] == 2

        question_response = client.post(
            f"/api/research/projects/{project_id}/files/{file_id}/questions",
            json={
                "version": 1,
                "anchor": {"quote": "Calibrated response"},
                "question": "What does this mean?",
            },
        )
        assert question_response.status_code == 201
        question = question_response.json()["question"]
        assert question["model"] == "deepseek-v4-flash"
        assert question["citations"][0]["block"] == "B0002"
        assert question["citations"][0]["quote"] == "Calibrated response"

        refreshed = client.get(
            f"/api/research/projects/{project_id}/files/{file_id}/review"
        ).json()
        assert len(refreshed["annotations"]) == 1
        assert len(refreshed["questions"]) == 1
    finally:
        app.dependency_overrides.clear()
