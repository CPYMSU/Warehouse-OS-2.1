from __future__ import annotations

import base64
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api import research as research_api
from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import system_session
from app.main import app
from app.services import research_review, research_semantic_refinement
from app.services.integrations import ModelConnection
from app.services.research_refinement import _assemble_docx, _normalized_blocks
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
              xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <w:body>
                <w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>MK51 Paper</w:t></w:r></w:p>
                <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Method</w:t></w:r></w:p>
                <w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Calibrated response</w:t></w:r>
                  <w:r><w:drawing><wp:docPr id="1" name="Figure 1"
                    descr="Calibration curve"/><a:blip r:embed="rId5"/></w:drawing></w:r>
                </w:p>
                <w:p><m:oMath><m:f><m:num><m:r><m:t>a</m:t></m:r></m:num><m:den><m:r><m:t>b</m:t></m:r></m:den></m:f></m:oMath></w:p>
                <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Sample</w:t></w:r></w:p></w:tc>
                  <w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
              </w:body>
            </w:document>""",
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId5"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
                Target="media/image1.png"/>
            </Relationships>""",
        )
        archive.writestr(
            "word/media/image1.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
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
        "image",
        "equation",
        "table_row",
    ]
    assert blocks[2].heading_path == ("MK51 Paper", "Method")
    assert "Calibrated response" in blocks[2].content
    assert blocks[3].content == "Calibration curve"
    assert blocks[3].locator["relationship_id"] == "rId5"
    assert blocks[3].locator["archive_path"] == "word/media/image1.png"
    assert blocks[4].content == "ab"
    assert blocks[5].content == "Sample | Value"
    assert blocks[5].locator["cells"] == ["Sample", "Value"]
    assert blocks[1].start_offset == len("MK51 Paper") + 2
    assert blocks[-1].end_offset > blocks[-1].start_offset


def test_docx_review_parser_recovers_legacy_vml_desktop_screenshot(tmp_path: Path) -> None:
    path = tmp_path / "legacy-screenshot.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
              <Default Extension="png" ContentType="image/png"/>
            </Types>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document
              xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
              xmlns:v="urn:schemas-microsoft-com:vml"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <w:body><w:p><w:pict><v:shape>
                <v:imagedata r:id="rIdLegacy"/>
              </v:shape></w:pict></w:p></w:body>
            </w:document>""",
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rIdLegacy"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
                Target="media/desktop%20shot.png"/>
            </Relationships>""",
        )
        archive.writestr(
            "word/media/desktop shot.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
        )

    blocks = parse_document_blocks(
        path,
        {
            "original_filename": path.name,
            "content_type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            "size_bytes": path.stat().st_size,
        },
    )

    assert len(blocks) == 1
    assert blocks[0].block_type == "image"
    assert blocks[0].locator["relationship_id"] == "rIdLegacy"
    assert blocks[0].locator["archive_path"] == "word/media/desktop shot.png"
    assert blocks[0].locator["content_type"] == "image/png"


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


def test_refinement_selection_anchor_is_verified_against_the_live_draft() -> None:
    draft = {
        "blocks": [
            {
                "id": "paragraph-1",
                "block_type": "paragraph",
                "text": "Calibrated response remains stable.",
            },
            {
                "id": "table-1",
                "block_type": "table",
                "cells": ["Sample", "Value"],
            },
        ]
    }

    anchor = research_semantic_refinement._validated_selection(
        draft,
        {
            "block_id": "paragraph-1",
            "field_name": "text",
            "start_offset": 0,
            "end_offset": 10,
            "quote": "Calibrated",
        },
    )

    assert anchor["quote"] == "Calibrated"
    assert anchor["source_sha256"]
    assert anchor["suffix"].startswith(" response")

    with pytest.raises(HTTPException) as error:
        research_semantic_refinement._validated_selection(
            draft,
            {
                "block_id": "table-1",
                "field_name": "cell",
                "cell_index": 1,
                "start_offset": 0,
                "end_offset": 5,
                "quote": "Wrong",
            },
        )
    assert error.value.status_code == 409


def test_content_refinement_reassembles_docx_text_figures_and_tables(tmp_path: Path) -> None:
    source = tmp_path / "paper.docx"
    target = tmp_path / "refined.docx"
    _paper_docx(source)
    parsed = parse_document_blocks(
        source,
        {
            "original_filename": "paper.docx",
            "content_type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            "size_bytes": source.stat().st_size,
        },
    )
    blocks = [
        {
            "id": block.stable_key,
            "type": block.block_type,
            "text": "Rewritten calibrated response"
            if block.block_type == "paragraph"
            else block.content,
            "level": block.heading_level,
            "cells": ["Sample", "Refined value"]
            if block.block_type == "table_row"
            else None,
            "source": block.locator,
        }
        for block in parsed
    ]
    normalized = _normalized_blocks(blocks, existing=blocks)
    target.write_bytes(_assemble_docx(source, normalized).read())

    refined = parse_document_blocks(
        target,
        {
            "original_filename": "paper.docx",
            "content_type": (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            "size_bytes": target.stat().st_size,
        },
    )

    assert any(block.content == "Rewritten calibrated response" for block in refined)
    assert any(block.block_type == "image" for block in refined)
    assert any(block.content == "Sample | Refined value" for block in refined)


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

    def semantic_completion(_connection: object, **kwargs: object) -> str:
        system_prompt = str(kwargs.get("system_prompt") or "")
        user_prompt = str(kwargs.get("user_prompt") or "")
        if "段落语义处理器" in system_prompt:
            source = __import__("json").loads(user_prompt)
            return __import__("json").dumps(
                {
                    "items": [
                        {
                            "block_id": item["block_id"],
                            "translation_zh_cn": "简中：" + str(item.get("text") or ""),
                            "distillation": "蒸馏：" + str(item.get("text") or ""),
                            "argument_role": "evidence",
                            "keywords": ["calibration"],
                        }
                        for item in source
                    ]
                },
                ensure_ascii=False,
            )
        if "语义孪生总索引员" in system_prompt:
            return (
                '{"summary":"全文蒸馏","research_question":"如何校准？",'
                '"method":"校准实验","findings":"响应稳定","limitations":"样本有限",'
                '"argument_outline":["方法","结果"],"glossary":[]}'
            )
        if kwargs.get("json_mode"):
            marker = "【原始区块 "
            start = user_prompt.find(marker)
            block_id = user_prompt[start + len(marker) :].split(" ·", 1)[0]
            return __import__("json").dumps(
                {
                    "summary": "评审完成",
                    "findings": [
                        {
                            "block_id": block_id,
                            "severity": "medium",
                            "category": "wording",
                            "quote": "MK51 Paper",
                            "rationale": "需要更明确的学术表达。",
                            "suggestion": "MK51 Calibration Study",
                            "evidence": [block_id],
                            "confidence": 0.8,
                        }
                    ],
                },
                ensure_ascii=False,
            )
        return "主 AI 已综合各评审，并保留原文证据区块。"

    monkeypatch.setattr(
        research_semantic_refinement,
        "connected_deepseek",
        lambda *_args: ModelConnection(
            base_url="https://model.invalid",
            model="test-research-model",
            api_key="test-only",
        ),
    )
    monkeypatch.setattr(
        research_semantic_refinement,
        "chat_completion",
        semantic_completion,
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
        assert workspace["index"]["block_count"] == 6
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

        refinement_response = client.post(
            f"/api/research/projects/{project_id}/files/{file_id}/refinement",
            json={},
        )
        assert refinement_response.status_code == 200
        refinement = refinement_response.json()
        assert refinement["capabilities"]["browser_compute"] is True
        assert refinement["capabilities"]["office_runtime_required"] is False
        assert len(refinement["draft"]["blocks"]) == 6
        figure = next(
            block for block in refinement["draft"]["blocks"] if block["type"] == "image"
        )
        assert figure["media_url"].endswith("?version=1")
        equation = next(
            block for block in refinement["draft"]["blocks"] if block["type"] == "equation"
        )
        assert equation["latex"] == r"\frac{a}{b}"
        media_response = client.get(figure["media_url"])
        assert media_response.status_code == 200
        assert media_response.headers["content-type"] == "image/png"
        draft_blocks = refinement["draft"]["blocks"]
        paragraph = next(block for block in draft_blocks if block["type"] == "paragraph")

        semantic_path = (
            f"/api/research/projects/{project_id}/files/{file_id}/refinement/semantic"
        )
        semantic_before = client.get(semantic_path)
        assert semantic_before.status_code == 200
        assert semantic_before.json()["capabilities"]["dedicated_runtime_required"] is False
        semantic_refresh = client.post(
            semantic_path + "/refresh",
            json={"modes": ["translate", "distill"]},
        )
        assert semantic_refresh.status_code == 202
        semantic_ready = client.get(semantic_path).json()
        assert semantic_ready["latest_run"]["status"] == "ready"
        assert any(
            item["artifact_kind"] == "document_digest"
            for item in semantic_ready["artifacts"]
        )
        paragraph_semantic = next(
            item
            for item in semantic_ready["artifacts"]
            if item["block_id"] == paragraph["id"]
        )
        assert paragraph_semantic["content"]["translation_zh_cn"].startswith("简中：")

        selection = {
            "block_id": paragraph["id"],
            "field_name": "text",
            "cell_index": None,
            "start_offset": 0,
            "end_offset": len("Calibrated"),
            "quote": "Calibrated",
        }
        draft_annotation = client.post(
            semantic_path.rsplit("/semantic", 1)[0] + "/annotations",
            json={
                "selection": selection,
                "annotation_type": "note",
                "color": "yellow",
                "body": "Explain the calibration boundary.",
            },
        )
        assert draft_annotation.status_code == 201
        annotation_id = draft_annotation.json()["annotation"]["id"]
        selected_chat = client.post(
            semantic_path.rsplit("/semantic", 1)[0] + "/agents/chief/messages",
            json={"message": "解释这个选区。", "selection": selection},
        )
        assert selected_chat.status_code == 201
        assert selected_chat.json()["message"]["citations"][0]["quote"] == "Calibrated"
        with_annotation = client.get(semantic_path).json()
        assert with_annotation["annotations"][0]["body"] == (
            "Explain the calibration boundary."
        )
        resolved_annotation = client.post(
            f"/api/research/manuscript-annotations/{annotation_id}/status",
            json={"resolved": True},
        )
        assert resolved_annotation.status_code == 200
        assert resolved_annotation.json()["status"] == "resolved"

        review_refresh = client.post(
            semantic_path + "/refresh",
            json={
                "modes": [
                    "review:neutrality",
                    "review:logic",
                    "review:clarity",
                    "review:professional",
                ]
            },
        )
        assert review_refresh.status_code == 202
        reviewed = client.get(semantic_path).json()
        assert reviewed["latest_run"]["status"] == "ready"
        assert {item["agent_type"] for item in reviewed["threads"]} == {
            "chief",
            "neutrality",
            "logic",
            "clarity",
            "professional",
        }
        assert len(reviewed["findings"]) == 4
        chief_chat = client.post(
            semantic_path.rsplit("/semantic", 1)[0] + "/agents/chief/messages",
            json={"message": "请综合四位评审。"},
        )
        assert chief_chat.status_code == 201
        assert "综合各评审" in chief_chat.json()["message"]["body"]

        paragraph["text"] = "Rewritten calibrated response"
        save_response = client.put(
            f"/api/research/projects/{project_id}/files/{file_id}/refinement",
            json={
                "expected_revision": refinement["draft"]["revision"],
                "blocks": draft_blocks,
            },
        )
        assert save_response.status_code == 200
        assert save_response.json()["draft"]["revision"] == 1
        stale_annotation = client.get(semantic_path).json()["annotations"][0]
        assert stale_annotation["status"] == "stale"
        stale_response = client.put(
            f"/api/research/projects/{project_id}/files/{file_id}/refinement",
            json={"expected_revision": 0, "blocks": draft_blocks},
        )
        assert stale_response.status_code == 409

        submit_response = client.post(
            f"/api/research/projects/{project_id}/files/{file_id}/refinement/submit",
            json={"expected_revision": 1, "commit_message": "Refine argument content"},
        )
        assert submit_response.status_code == 200
        submitted = submit_response.json()
        assert submitted["version"]["version"] == 2
        assert submitted["version"]["commit_message"] == "Refine argument content"
        assert submitted["draft_revision"] == 2

        latest_review = client.get(
            f"/api/research/projects/{project_id}/files/{file_id}/review"
        ).json()
        assert any(
            block["content"] == "Rewritten calibrated response"
            for block in latest_review["blocks"]
        )
        assert any(block["block_type"] == "image" for block in latest_review["blocks"])
    finally:
        app.dependency_overrides.clear()
