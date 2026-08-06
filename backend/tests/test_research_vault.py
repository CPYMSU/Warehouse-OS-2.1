from __future__ import annotations

import hashlib
import io
import sqlite3
import subprocess
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers
from starlette.requests import Request

from app.api import research as research_api
from app.api.deps import ActorContext, _runtime_api_scope
from app.core.config import Settings
from app.services.research_execution import _arguments, _safe_path, execution_runtimes
from app.services.research_vault import (
    ResearchGitRepository,
    _require_read,
    _require_write,
    analyse_object,
    research_asset_class,
    research_formats,
)
from app.terminal.catalog import business_action_catalogue

RESEARCH_TOOLS = {
    "research_api_key_issue",
    "research_api_keys_list",
    "research_api_key_revoke",
    "research_cli_show",
    "research_cli_show",
    "research_formats_list",
    "research_project_list",
    "research_project_create",
    "research_project_show",
    "research_upload_contract",
    "research_git_log",
    "research_file_versions",
    "research_file_preview",
    "research_document_review",
    "research_manuscript_refinement",
    "research_manuscript_draft_save",
    "research_manuscript_submit",
    "research_document_annotate",
    "research_document_ask",
    "research_file_diff",
    "research_workflow_show",
    "research_dmp_show",
    "research_dmp_update",
    "research_protocol_list",
    "research_protocol_create",
    "research_run_list",
    "research_run_start",
    "research_run_complete",
    "research_claim_list",
    "research_claim_create",
    "research_evidence_link",
    "research_review_list",
    "research_review_submit",
    "research_reproduce_check",
    "research_execution_runtimes",
    "research_execution_list",
    "research_execution_submit",
    "research_execution_show",
    "research_execution_cancel",
    "research_execution_retry",
    "research_artifact_promote",
    "research_release_list",
    "research_release_create",
    "research_release_show",
}


def _actor(*permissions: str, role_level: int = 10) -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000002"),
        tenant_slug="research-test",
        tenant_name="Research Test",
        industry_template_key="research_lab",
        username="researcher",
        display_name="Researcher",
        role_level=role_level,
        topology_level=role_level,
        topology_title="Researcher",
        permissions=frozenset(permissions),
    )


def test_research_routes_and_capability_catalogue_share_exact_permissions() -> None:
    l10_without_permissions = _actor()
    with pytest.raises(HTTPException) as read_denied:
        _require_read(l10_without_permissions)
    with pytest.raises(HTTPException) as write_denied:
        _require_write(l10_without_permissions)
    assert read_denied.value.status_code == 403
    assert write_denied.value.status_code == 403

    reader = _actor("research.read", role_level=4)
    writer = _actor("research.write", role_level=4)
    _require_read(reader)
    _require_write(writer)

    reader_actions = {
        item["tool_name"]: item
        for item in business_action_catalogue(reader)
        if item["category"] == "research"
    }
    assert set(reader_actions) == RESEARCH_TOOLS
    assert reader_actions["research_formats_list"]["authorized"] is True
    assert reader_actions["research_api_key_issue"]["authorized"] is True
    assert reader_actions["research_api_keys_list"]["authorized"] is True
    assert reader_actions["research_api_key_revoke"]["authorized"] is True
    assert reader_actions["research_cli_show"]["authorized"] is True
    assert reader_actions["research_cli_show"]["authorized"] is True
    assert reader_actions["research_project_list"]["authorized"] is True
    assert reader_actions["research_project_show"]["authorized"] is True
    assert reader_actions["research_git_log"]["authorized"] is True
    assert reader_actions["research_file_versions"]["authorized"] is True
    assert reader_actions["research_file_preview"]["authorized"] is True
    assert reader_actions["research_manuscript_refinement"]["authorized"] is False
    assert reader_actions["research_manuscript_draft_save"]["authorized"] is False
    assert reader_actions["research_manuscript_submit"]["authorized"] is False
    assert reader_actions["research_file_diff"]["authorized"] is True
    assert reader_actions["research_workflow_show"]["authorized"] is True
    assert reader_actions["research_dmp_show"]["authorized"] is True
    assert reader_actions["research_protocol_list"]["authorized"] is True
    assert reader_actions["research_run_list"]["authorized"] is True
    assert reader_actions["research_claim_list"]["authorized"] is True
    assert reader_actions["research_review_list"]["authorized"] is True
    assert reader_actions["research_release_list"]["authorized"] is True
    assert reader_actions["research_release_show"]["authorized"] is True
    assert reader_actions["research_execution_runtimes"]["authorized"] is True
    assert reader_actions["research_execution_list"]["authorized"] is True
    assert reader_actions["research_execution_show"]["authorized"] is True
    assert reader_actions["research_project_create"]["authorized"] is False
    assert reader_actions["research_upload_contract"]["authorized"] is False
    assert reader_actions["research_dmp_update"]["authorized"] is False
    assert reader_actions["research_review_submit"]["authorized"] is False
    assert reader_actions["research_release_create"]["authorized"] is False

    writer_actions = {
        item["tool_name"]: item
        for item in business_action_catalogue(writer)
        if item["category"] == "research"
    }
    assert writer_actions["research_project_create"]["authorized"] is True
    assert writer_actions["research_upload_contract"]["authorized"] is True
    assert writer_actions["research_manuscript_refinement"]["authorized"] is True
    assert writer_actions["research_manuscript_draft_save"]["authorized"] is True
    assert writer_actions["research_manuscript_submit"]["authorized"] is True
    assert writer_actions["research_api_key_issue"]["authorized"] is True
    assert writer_actions["research_api_keys_list"]["authorized"] is True
    assert writer_actions["research_api_key_revoke"]["authorized"] is True
    assert writer_actions["research_cli_show"]["authorized"] is True
    assert writer_actions["research_dmp_update"]["authorized"] is True
    assert writer_actions["research_protocol_create"]["authorized"] is True
    assert writer_actions["research_run_start"]["authorized"] is True
    assert writer_actions["research_run_complete"]["authorized"] is True
    assert writer_actions["research_claim_create"]["authorized"] is True
    assert writer_actions["research_evidence_link"]["authorized"] is True
    assert writer_actions["research_reproduce_check"]["authorized"] is True
    assert writer_actions["research_execution_submit"]["authorized"] is True
    assert writer_actions["research_execution_cancel"]["authorized"] is True
    assert writer_actions["research_execution_retry"]["authorized"] is True
    assert writer_actions["research_artifact_promote"]["authorized"] is True
    assert writer_actions["research_review_submit"]["authorized"] is False
    assert writer_actions["research_release_create"]["authorized"] is False
    assert writer_actions["research_project_list"]["authorized"] is False


def test_research_execution_contract_rejects_shell_and_unsafe_paths() -> None:
    actor = _actor("research.read", role_level=4)
    contract = execution_runtimes(actor)
    assert contract["runtimes"][0]["key"] == "python-3.13"
    assert contract["isolation"] == {
        "network": "disabled",
        "root_filesystem": "read_only",
        "process_user": "unique_per_job",
        "shell": "disabled",
        "inputs": "immutable_file_versions",
        "outputs": "sha256_verified",
    }
    assert _safe_path("analysis/main.py", label="entrypoint") == "analysis/main.py"
    assert _arguments(["--seed", 42]) == ["--seed", "42"]
    for unsafe in ("/tmp/main.py", "../main.py", "analysis/../../secret"):
        with pytest.raises(HTTPException):
            _safe_path(unsafe, label="entrypoint")


def test_openapi_exposes_research_execution_lifecycle() -> None:
    paths = research_api.router.routes
    route_paths = {getattr(route, "path", "") for route in paths}
    assert "/api/research/execution-runtimes" in route_paths
    assert "/api/research/projects/{project_ref}/executions" in route_paths
    assert "/api/research/projects/{project_ref}/executions/{execution_ref}" in route_paths
    assert (
        "/api/research/projects/{project_ref}/executions/{execution_ref}/artifacts/"
        "{artifact_ref}/promote"
    ) in route_paths


def test_research_runtime_scope_and_streaming_upload_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    actor = _actor("research.read", "research.write", role_level=4)
    settings = Settings(
        asset_storage_root=tmp_path / "objects",
        research_repository_root=tmp_path / "git",
        research_max_upload_bytes=1024,
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/research/projects/study/files",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )
    assert _runtime_api_scope(request) == "research"
    assert research_formats(actor, settings)["upload"] == {
        "protocol": "multipart/form-data",
        "max_bytes": 1024,
        "checksum": "sha256",
        "content_addressed": True,
        "creates_file_version": True,
        "creates_git_commit": True,
    }

    content = b"sample,value\nA,1\n"
    digest = hashlib.sha256(content).hexdigest()
    observed: dict[str, object] = {}

    def fake_add_file_version(live_actor, project_ref, **kwargs):
        observed.update(actor=live_actor, project_ref=project_ref, **kwargs)
        return {
            "ok": True,
            "version": {"version": 1, "content_sha256": kwargs["stored"].sha256},
        }

    monkeypatch.setattr(research_api, "add_file_version", fake_add_file_version)
    result = research_api.research_file_upload(
        "study",
        actor,
        settings,
        UploadFile(
            file=io.BytesIO(content),
            filename="observations.csv",
            headers=Headers({"content-type": "text/csv"}),
        ),
        logical_path="data/observations.csv",
        commit_message="Add observations",
        expected_sha256=digest,
    )

    assert result["version"] == {"version": 1, "content_sha256": digest}
    stored = observed["stored"]
    assert stored.size_bytes == len(content)
    assert stored.sha256 == digest
    assert (settings.asset_storage_root / stored.object_key).read_bytes() == content
    assert observed["logical_path"] == "data/observations.csv"
    assert observed["commit_message"] == "Add observations"


def test_research_preview_adapters_extract_html_csv_and_docx(tmp_path: Path) -> None:
    html_path = tmp_path / "paper.html"
    html_path.write_text(
        "<article><h1>Result</h1><p>Visible finding</p><script>hiddenSecret()</script></article>",
        encoding="utf-8",
    )
    html = analyse_object(html_path, html_path.name, "text/html", html_path.stat().st_size)
    assert html.file_kind == "html"
    assert "Visible finding" in (html.extracted_text or "")
    assert "hiddenSecret" not in (html.extracted_text or "")
    assert html.preview["renderer"] == "sandboxed_html"

    csv_path = tmp_path / "observations.csv"
    csv_path.write_text("sample,value\nA,1\nB,2\n", encoding="utf-8")
    dataset = analyse_object(csv_path, csv_path.name, "text/csv", csv_path.stat().st_size)
    assert dataset.file_kind == "dataset"
    assert dataset.preview["columns"] == ["sample", "value"]
    assert dataset.preview["rows"] == [["A", "1"], ["B", "2"]]

    docx_path = tmp_path / "protocol.docx"
    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                'wordprocessingml/2006/main"><w:body><w:p>'
                "<w:r><w:t>Controlled protocol</w:t></w:r>"
                "</w:p></w:body></w:document>"
            ),
        )
    document = analyse_object(
        docx_path,
        docx_path.name,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        docx_path.stat().st_size,
    )
    assert document.file_kind == "document"
    assert document.extracted_text == "Controlled protocol"


def test_research_asset_taxonomy_separates_purpose_from_file_format() -> None:
    assert research_asset_class("administration/import-manifest.json", "code") == "administration"
    assert research_asset_class("code/integration/plots_compare_dbic_scanner.py", "code") == "code"
    assert research_asset_class("manuscript/mk51.docx", "document") == "manuscript"
    assert research_asset_class("references/shock-resilience.pdf", "pdf") == "literature"
    assert research_asset_class("data/panel.csv", "dataset") == "dataset"
    assert research_asset_class("results/model.sqlite", "database") == "database"
    assert research_asset_class("analysis/exploration.ipynb", "notebook") == "notebook"
    assert research_asset_class("figures/figure-01.png", "image") == "figure"


def test_research_preview_reads_sqlite_without_mutating_it(tmp_path: Path) -> None:
    database_path = tmp_path / "results.sqlite"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE observations(sample TEXT PRIMARY KEY, value REAL)")
    connection.executemany(
        "INSERT INTO observations(sample, value) VALUES (?, ?)",
        [("A", 1.25), ("B", 2.5)],
    )
    connection.commit()
    connection.close()

    before = database_path.read_bytes()
    preview = analyse_object(
        database_path,
        database_path.name,
        "application/vnd.sqlite3",
        database_path.stat().st_size,
    )

    assert preview.file_kind == "database"
    assert preview.preview["renderer"] == "database"
    assert preview.preview["tables"] == [
        {
            "name": "observations",
            "type": "table",
            "columns": ["sample", "value"],
            "rows": [["A", 1.25], ["B", 2.5]],
            "sample_rows": 2,
        }
    ]
    assert "CREATE TABLE observations" in (preview.extracted_text or "")
    assert database_path.read_bytes() == before


def test_research_git_repository_records_native_parented_commits(tmp_path: Path) -> None:
    repository = ResearchGitRepository(tmp_path, uuid4(), uuid4())
    first_sha, first_parent = repository.commit(
        branch="main",
        message="Initialize research project",
        manifest={"schema": "warehouse-research-manifest/v1", "files": []},
        author_name="Researcher",
        author_email="researcher@example.test",
    )
    second_sha, second_parent = repository.commit(
        branch="main",
        message="Add observations",
        manifest={
            "schema": "warehouse-research-manifest/v1",
            "files": [{"logical_path": "data/observations.csv", "version": 1}],
        },
        author_name="Researcher",
        author_email="researcher@example.test",
    )

    assert len(first_sha) == 40
    assert first_parent is None
    assert len(second_sha) == 40
    assert second_sha != first_sha
    assert second_parent == first_sha
    messages = subprocess.run(
        ["git", "-C", str(repository.path), "log", "--format=%s"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert messages == ["Add observations", "Initialize research project"]
