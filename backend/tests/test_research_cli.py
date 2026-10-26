from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import ActorContext, current_actor
from app.main import app
from app.research_cli import CliError, KEY_ENV, VERSION, ResearchClient, build_parser, main

TEST_KEY = "wsk_bonfire_012345abcdef_abcdefghijklmnopqrstuvwxyzABCDEF"


class _UploadResponse:
    status = 201
    reason = "Created"

    def read(self) -> bytes:
        return b'{"ok":true,"file":{"logical_path":"data/input.csv"}}'

    def getheader(self, name: str, default: str | None = None) -> str | None:
        values = {"Content-Type": "application/json", "X-Request-ID": "upload-request"}
        return values.get(name, default)


class _FakeConnection:
    latest: _FakeConnection | None = None

    def __init__(self, host: str, port: int | None, **kwargs: object) -> None:
        self.host = host
        self.port = port
        self.kwargs = kwargs
        self.headers: dict[str, str] = {}
        self.body = bytearray()
        _FakeConnection.latest = self

    def putrequest(self, method: str, target: str) -> None:
        self.method = method
        self.target = target

    def putheader(self, name: str, value: str) -> None:
        self.headers[name] = value

    def endheaders(self) -> None:
        return

    def send(self, value: bytes | bytearray) -> None:
        self.body.extend(value)

    def getresponse(self) -> _UploadResponse:
        return _UploadResponse()

    def close(self) -> None:
        return


class _DownloadResponse:
    def __init__(self, content: bytes) -> None:
        self._body = io.BytesIO(content)
        self.headers = {
            "X-Content-SHA256": hashlib.sha256(content).hexdigest(),
            "X-Request-ID": "download-request",
        }

    def __enter__(self) -> _DownloadResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)


class _DownloadOpener:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.request = None

    def open(self, request, timeout: float):  # noqa: ANN001
        self.request = request
        self.timeout = timeout
        return _DownloadResponse(self.content)


def _actor() -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="bonfire",
        tenant_name="Bonfire",
        industry_template_key="research_lab",
        username="researcher@example.com",
        display_name="Researcher",
        role_level=10,
        topology_level=10,
        topology_title="Research Director",
        permissions=frozenset({"research.read", "research.write", "research.review"}),
    )


def test_cli_uses_environment_key_without_echoing_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed: dict[str, object] = {}

    def fake_request(client: ResearchClient, method: str, path: str, payload=None):
        observed.update(key=client.key, method=method, path=path, payload=payload)
        return {"user": {"display_name": "Researcher"}, "tenant": "bonfire"}

    monkeypatch.setattr(ResearchClient, "request", fake_request)
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    result = main(["whoami"])
    captured = capsys.readouterr()

    assert result == 0
    assert json.loads(captured.out)["tenant"] == "bonfire"
    assert TEST_KEY not in captured.out + captured.err
    assert observed == {
        "key": TEST_KEY,
        "method": "GET",
        "path": "/api/auth/me",
        "payload": None,
    }


def test_cli_streams_checksum_verified_multipart_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("app.research_cli.http.client.HTTPConnection", _FakeConnection)
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    source = tmp_path / "觀測.csv"
    source.write_bytes(b"sample,value\nA,1\n")
    result = main(
        [
            "--base-url",
            "http://127.0.0.1:8080",
            "file",
            "upload",
            "--project",
            "project-one",
            "--file",
            str(source),
            "--path",
            "data/input.csv",
            "--message",
            "Add input",
        ]
    )
    output = json.loads(capsys.readouterr().out)
    connection = _FakeConnection.latest

    assert result == 0
    assert output["ok"] is True
    assert connection is not None
    assert connection.headers["Authorization"] == f"Bearer {TEST_KEY}"
    assert connection.headers["Content-Type"].startswith("multipart/form-data; boundary=")
    assert source.read_bytes() in connection.body
    assert hashlib.sha256(source.read_bytes()).hexdigest().encode() in connection.body
    assert b"filename*=UTF-8''" in connection.body


def test_cli_downloads_atomically_and_verifies_server_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    content = b"project,value\nalpha,42\n"
    opener = _DownloadOpener(content)
    monkeypatch.setattr("app.research_cli.urllib.request.build_opener", lambda *args: opener)
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    output_path = tmp_path / "result.csv"
    result = main(
        [
            "--base-url",
            "http://127.0.0.1:8080",
            "file",
            "download",
            "--project",
            "project-one",
            "--file",
            "file-one",
            "--output",
            str(output_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert result == 0
    assert output_path.read_bytes() == content
    assert output["verified"] is True
    assert output["sha256"] == hashlib.sha256(content).hexdigest()
    assert opener.request.get_header("Authorization") == f"Bearer {TEST_KEY}"


def test_cli_watch_returns_machine_readable_terminal_state(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        ResearchClient,
        "request",
        lambda *args, **kwargs: {
            "execution": {"id": "execution-id", "status": "succeeded"},
            "events": [],
            "artifacts": [],
        },
    )
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    result = main(
        [
            "--base-url",
            "http://127.0.0.1:8080",
            "execution",
            "watch",
            "--project",
            "project-one",
            "--execution",
            "execution-one",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert result == 0
    assert output["execution"]["status"] == "succeeded"
    assert output["watch"]["terminal"] is True


def test_cli_document_ask_sends_versioned_anchor_and_question(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed: dict[str, object] = {}

    def fake_request(client: ResearchClient, method: str, path: str, payload=None):
        observed.update(method=method, path=path, payload=payload)
        return {"ok": True, "question": {"answer": "Grounded answer"}}

    monkeypatch.setattr(ResearchClient, "request", fake_request)
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    result = main(
        [
            "document",
            "ask",
            "--project",
            "mk51",
            "--file",
            "manuscript/paper.docx",
            "--version",
            "3",
            "--question",
            "What does this mean?",
            "--anchor",
            '{"quote":"selected text","prefix":"before ","suffix":" after"}',
        ]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert observed == {
        "method": "POST",
        "path": "/api/research/projects/mk51/files/manuscript%2Fpaper.docx/questions",
        "payload": {
            "version": 3,
            "anchor": {
                "quote": "selected text",
                "prefix": "before ",
                "suffix": " after",
            },
            "question": "What does this mean?",
        },
    }


def test_cli_rejects_remote_plain_http_and_has_no_plaintext_key_argument(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    result = main(["--base-url", "http://example.com", "whoami"])

    assert result == 2
    assert json.loads(capsys.readouterr().err)["error"]["type"] == "cli_error"
    option_strings = {
        option
        for action in build_parser()._actions
        for option in action.option_strings
    }
    assert "--key" not in option_strings
    assert "--key-file" in option_strings


def test_authenticated_cli_manifest_and_download_match() -> None:
    app.dependency_overrides[current_actor] = _actor
    try:
        client = TestClient(app)
        manifest_response = client.get("/api/research/cli/manifest")
        download_response = client.get("/api/research/cli/download")
    finally:
        app.dependency_overrides.clear()

    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["version"] == VERSION
    assert manifest["credential_scope"] == "research"
    assert len(manifest["commands"]) >= 15
    assert download_response.status_code == 200
    assert hashlib.sha256(download_response.content).hexdigest() == manifest["sha256"]
    assert download_response.headers["x-content-sha256"] == manifest["sha256"]
    assert b"def main(" in download_response.content


def test_collaboration_context_exports_prompt_without_credentials(tmp_path, monkeypatch, capsys):
    observed = []

    def request(client, method, path, payload=None):
        observed.append((method, path))
        return {"schema": "bonfire.research.collaboration.v1", "prompt": "Use the current data version.\n保存研究產物。"}

    monkeypatch.setattr(ResearchClient, "request", request)
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    output = tmp_path / "AGENTS.md"
    assert main(["collaboration", "context", "--project", "mk51", "--stage", "dynamic_equilibrium", "--format", "prompt", "--output", str(output)]) == 0
    assert "保存研究產物" in output.read_text(encoding="utf-8")
    assert json.loads(capsys.readouterr().out)["format"] == "prompt"
    assert observed == [("GET", "/api/research/projects/mk51/collaboration?stage=dynamic_equilibrium")]
    assert main(["collaboration", "context", "--project", "mk51", "--stage", "question", "--format", "prompt"]) == 0
    rendered = capsys.readouterr().out
    assert rendered.startswith("Use the current data version.")
    assert TEST_KEY not in rendered + output.read_text(encoding="utf-8")


def test_stage_save_accepts_versioned_payload_file_and_explicit_fields(tmp_path, monkeypatch, capsys):
    observed = []
    payload = tmp_path / "stage.json"
    payload.write_text(json.dumps({"discipline": "econometrics", "expected_revision": 2, "notes": "Current model", "plan": "Compare estimators"}), encoding="utf-8")
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    monkeypatch.setattr(ResearchClient, "request", lambda client, method, path, payload=None: observed.append((method, path, payload)) or {"ok": True})
    assert main(["stage", "save", "--project", "mk51", "--stage", "econometric_model", "--payload", "@" + str(payload), "--status", "blocked", "--blockers", "Need variable definitions", "--assignee", "shared"]) == 0
    assert observed == [("PUT", "/api/research/projects/mk51/discipline-workflow/stages/econometric_model", {
        "discipline": "econometrics", "expected_revision": 2, "notes": "Current model", "plan": "Compare estimators",
        "status": "blocked", "blockers": "Need variable definitions", "assignee": "shared",
    })]
    assert json.loads(capsys.readouterr().out)["ok"] is True


def _collaboration_context():
    return {"discipline": {"key": "econometrics"}, "permissions": {"can_write": True}, "stage": {
        "key": "question", "revision": 3, "notes": "Keep the research question", "status": "blocked",
        "plan": "Compare assumptions", "findings": "Preliminary association", "blockers": "Need more data",
        "next_action": "Check missingness", "assignee": "shared",
        "artifacts": [{"file_version_id": "old-version", "role": "design", "title": "Study design", "download_path": "/safe/download"}],
    }}


def test_collaboration_publish_preserves_stage_and_binds_uploaded_version(tmp_path, monkeypatch, capsys):
    source = tmp_path / "curve.html"
    source.write_text("<html>Research visualization</html>", encoding="utf-8")
    observed = []

    def request(client, method, path, payload=None):
        observed.append((method, path, payload))
        if method == "GET":
            context = _collaboration_context()
            context["stage"]["artifact_references"] = [
                {"file_version_id": "old-version", "role": "design", "title": "Study design"},
                {"file_version_id": "unavailable-version", "role": "report", "title": "Retained historical reference"},
            ]
            return context
        return {"ok": True}

    def upload(client, path, uploaded_source, **kwargs):
        assert uploaded_source == source.resolve()
        assert kwargs["expected_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert kwargs["logical_path"] == "results/question/curve.html"
        return {"version": {"id": "new-version"}, "file": {"id": "file-one"}}

    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    monkeypatch.setattr(ResearchClient, "request", request)
    monkeypatch.setattr(ResearchClient, "upload", upload)
    assert main(["collaboration", "publish", "--project", "mk51", "--stage", "question", "--file", str(source), "--role", "visualization"]) == 0
    assert observed[1] == ("PUT", "/api/research/projects/mk51/discipline-workflow/stages/question", {
        "discipline": "econometrics", "expected_revision": 3, "notes": "Keep the research question", "status": "blocked",
        "plan": "Compare assumptions", "findings": "Preliminary association", "blockers": "Need more data",
        "next_action": "Check missingness", "assignee": "shared",
        "artifacts": [{"file_version_id": "old-version", "role": "design", "title": "Study design"},
                      {"file_version_id": "unavailable-version", "role": "report", "title": "Retained historical reference"},
                      {"file_version_id": "new-version", "role": "visualization", "title": "curve.html"}],
    })
    assert json.loads(capsys.readouterr().out)["attached"] is True


def test_collaboration_publish_rejects_long_explicit_title_before_network(tmp_path, monkeypatch, capsys):
    source = tmp_path / "curve.html"
    source.write_text("plot", encoding="utf-8")
    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    monkeypatch.setattr(ResearchClient, "request", lambda *args, **kwargs: pytest.fail("Title must be checked before the context request"))
    assert main(["collaboration", "publish", "--project", "mk51", "--stage", "question", "--file", str(source), "--role", "visualization", "--title", "x" * 201]) == 2
    assert "at most 200" in json.loads(capsys.readouterr().err)["error"]["message"]


@pytest.mark.parametrize("stale_before_upload", [False, True])
def test_collaboration_publish_never_overwrites_conflicting_stage(tmp_path, monkeypatch, capsys, stale_before_upload):
    source = tmp_path / "results.csv"
    source.write_bytes(b"x,y\n1,2\n")
    uploads = []
    writes = []

    def request(client, method, path, payload=None):
        if method == "GET":
            return _collaboration_context()
        writes.append(payload)
        raise CliError("Stage changed", kind="http_error", status=409, exit_code=3)

    def upload(*args, **kwargs):
        uploads.append(kwargs)
        return {"version": {"id": "retained-version"}}

    monkeypatch.setenv(KEY_ENV, TEST_KEY)
    monkeypatch.setattr(ResearchClient, "request", request)
    monkeypatch.setattr(ResearchClient, "upload", upload)
    args = ["collaboration", "publish", "--project", "mk51", "--stage", "question", "--file", str(source), "--role", "dataset"]
    if stale_before_upload:
        args += ["--expected-revision", "1"]
    assert main(args) == 3
    captured = capsys.readouterr()
    error = json.loads(captured.err)["error"]
    if stale_before_upload:
        assert error["type"] == "revision_conflict"
        assert uploads == [] and writes == []
    else:
        assert error["type"] == "artifact_attachment_failed"
        assert error["detail"]["file_version_id"] == "retained-version"
        assert len(uploads) == 1 and len(writes) == 1
    assert TEST_KEY not in captured.out + captured.err
