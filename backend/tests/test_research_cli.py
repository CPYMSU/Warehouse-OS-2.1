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
from app.research_cli import KEY_ENV, VERSION, ResearchClient, build_parser, main

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
