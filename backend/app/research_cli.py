#!/usr/bin/env python3
"""Headless CLI for the tenant-scoped Warehouse Research API.

This module deliberately uses only the Python standard library so the same
file can be downloaded from Warehouse OS and executed without installing the
server package.  Credentials are read from the environment or a protected
file; they are never accepted as command-line values.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import mimetypes
import os
import secrets
import ssl
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = "1.1.0"
DEFAULT_BASE_URL = "https://bonfirework.org"
KEY_ENV = "WAREHOUSE_RESEARCH_KEY"
BASE_URL_ENV = "WAREHOUSE_BASE_URL"
TERMINAL_EXECUTION_STATUSES = frozenset(
    {"succeeded", "failed", "cancelled", "timed_out"}
)
CLI_COMMANDS = (
    "whoami",
    "formats",
    "project list|create|show|commits",
    "file upload|versions|preview|diff|download",
    "document review|annotate|ask",
    "workflow show",
    "dmp show|update",
    "protocol list|create",
    "run list|start|update",
    "claim list|create",
    "evidence link",
    "review list|submit",
    "reproduce check",
    "execution runtimes|list|submit|show|watch|cancel|retry",
    "artifact download|promote",
    "release list|create|show",
)


class CliError(RuntimeError):
    """A safe, user-facing CLI error."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "cli_error",
        status: int | None = None,
        request_id: str | None = None,
        detail: object | None = None,
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.request_id = request_id
        self.detail = detail
        self.exit_code = exit_code

    def payload(self) -> dict[str, object]:
        error: dict[str, object] = {"type": self.kind, "message": str(self)}
        if self.status is not None:
            error["status"] = self.status
        if self.request_id:
            error["request_id"] = self.request_id
        if self.detail not in (None, ""):
            error["detail"] = self.detail
        return {"ok": False, "error": error}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward a bearer credential through an HTTP redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _print_json(value: object, *, compact: bool = False, stream=None) -> None:
    target = stream or sys.stdout
    json.dump(
        value,
        target,
        ensure_ascii=False,
        indent=None if compact else 2,
        separators=(",", ":") if compact else None,
    )
    target.write("\n")


def _read_json(value: str | None, *, label: str, expected: type) -> Any:
    if value is None:
        return None
    source = value
    if value.startswith("@"):
        path = Path(value[1:]).expanduser()
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(f"Cannot read {label} JSON file: {exc}") from exc
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise CliError(f"Invalid {label} JSON: {exc.msg}") from exc
    if not isinstance(parsed, expected):
        raise CliError(f"{label} must be a JSON {expected.__name__}")
    return parsed


def _ref(value: object) -> str:
    return urllib.parse.quote(str(value), safe="")


def _with_query(path: str, **values: object) -> str:
    query = urllib.parse.urlencode(
        {key: value for key, value in values.items() if value is not None}
    )
    return f"{path}?{query}" if query else path


def _field(payload: dict[str, object], key: str, value: object) -> None:
    if value is not None:
        payload[key] = value


def _validate_base_url(raw: str, *, allow_insecure_http: bool) -> str:
    value = raw.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CliError("Base URL must be an absolute http:// or https:// URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CliError("Base URL cannot contain credentials, query, or fragment")
    if parsed.scheme == "http" and parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    } and not allow_insecure_http:
        raise CliError(
            "Refusing to send a Research API Key over remote HTTP; use HTTPS"
        )
    return value


def _read_key(key_file: str | None) -> str:
    if key_file:
        path = Path(key_file).expanduser()
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
            if os.name == "posix" and mode & 0o077:
                raise CliError(
                    f"Key file permissions are too broad ({mode:o}); run chmod 600 {path}"
                )
            key = path.read_text(encoding="utf-8").strip()
        except CliError:
            raise
        except OSError as exc:
            raise CliError(f"Cannot read Research API Key file: {exc}") from exc
    else:
        key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise CliError(
            f"Research API Key is required in {KEY_ENV} or --key-file"
        )
    if not key.startswith("wsk_") or any(character.isspace() for character in key):
        raise CliError("Research API Key has an invalid format")
    return key


def _decode_response(body: bytes, content_type: str) -> object:
    if not body:
        return {"ok": True}
    text = body.decode("utf-8", errors="replace")
    if "json" in content_type.lower() or text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return {"ok": True, "text": text}


@dataclass
class ResearchClient:
    base_url: str
    key: str
    timeout: float

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
            "User-Agent": f"bonfire-research/{VERSION}",
            "X-Request-ID": secrets.token_hex(16),
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> object:
        data = _json_bytes(payload) if payload is not None else None
        headers = self._headers
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self._url(path), data=data, headers=headers, method=method
        )
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(request, timeout=self.timeout) as response:
                return _decode_response(
                    response.read(), response.headers.get("Content-Type", "")
                )
        except urllib.error.HTTPError as exc:
            body = exc.read()
            decoded = _decode_response(body, exc.headers.get("Content-Type", ""))
            detail = decoded.get("detail") if isinstance(decoded, dict) else decoded
            message = str(detail or exc.reason or f"HTTP {exc.code}")
            raise CliError(
                message,
                kind="http_error",
                status=exc.code,
                request_id=exc.headers.get("X-Request-ID"),
                detail=decoded,
                exit_code=3,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise CliError(
                f"Research API request failed: {reason}",
                kind="network_error",
                exit_code=4,
            ) from exc

    def upload(
        self,
        path: str,
        source: Path,
        *,
        logical_path: str | None,
        commit_message: str | None,
        expected_sha256: str | None,
    ) -> object:
        boundary = f"----bonfire-research-{secrets.token_hex(18)}"
        fields = {
            "logical_path": logical_path,
            "commit_message": commit_message,
            "expected_sha256": expected_sha256,
        }
        prefix = bytearray()
        for name, value in fields.items():
            if value is None:
                continue
            prefix.extend(f"--{boundary}\r\n".encode())
            prefix.extend(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
            )
            prefix.extend(str(value).encode("utf-8"))
            prefix.extend(b"\r\n")
        filename = source.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
        ascii_filename = "".join(
            character if 32 <= ord(character) < 127 else "_" for character in filename
        )
        encoded_filename = urllib.parse.quote(filename, safe="")
        content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        prefix.extend(f"--{boundary}\r\n".encode())
        prefix.extend(
            (
                f'Content-Disposition: form-data; name="file"; filename="{ascii_filename}"; '
                f"filename*=UTF-8''{encoded_filename}\r\n"
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
        )
        suffix = f"\r\n--{boundary}--\r\n".encode()
        content_length = len(prefix) + source.stat().st_size + len(suffix)
        parsed = urllib.parse.urlsplit(self._url(path))
        connection_class = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        kwargs: dict[str, object] = {"timeout": self.timeout}
        if parsed.scheme == "https":
            kwargs["context"] = ssl.create_default_context()
        connection = connection_class(parsed.hostname, parsed.port, **kwargs)
        target = urllib.parse.urlunsplit(("", "", parsed.path, parsed.query, ""))
        try:
            connection.putrequest("POST", target)
            for name, value in self._headers.items():
                connection.putheader(name, value)
            connection.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
            connection.putheader("Content-Length", str(content_length))
            connection.endheaders()
            connection.send(prefix)
            with source.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    connection.send(chunk)
            connection.send(suffix)
            response = connection.getresponse()
            body = response.read()
            decoded = _decode_response(body, response.getheader("Content-Type", ""))
            if response.status >= 400:
                detail = decoded.get("detail") if isinstance(decoded, dict) else decoded
                raise CliError(
                    str(detail or response.reason),
                    kind="http_error",
                    status=response.status,
                    request_id=response.getheader("X-Request-ID"),
                    detail=decoded,
                    exit_code=3,
                )
            if 300 <= response.status < 400:
                raise CliError(
                    "Research upload refused an HTTP redirect",
                    kind="redirect_refused",
                    status=response.status,
                    exit_code=3,
                )
            return decoded
        except CliError:
            raise
        except (TimeoutError, OSError, http.client.HTTPException) as exc:
            raise CliError(
                f"Research upload failed: {exc}",
                kind="network_error",
                exit_code=4,
            ) from exc
        finally:
            connection.close()

    def download(
        self,
        path: str,
        destination: Path,
        *,
        force: bool,
    ) -> dict[str, object]:
        destination = Path(os.path.abspath(destination.expanduser()))
        if destination.exists() and not force:
            raise CliError(f"Output already exists: {destination}; pass --force to replace it")
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            self._url(path), headers=self._headers, method="GET"
        )
        opener = urllib.request.build_opener(_NoRedirect())
        temporary: Path | None = None
        try:
            with opener.open(request, timeout=self.timeout) as response:
                expected = response.headers.get("X-Content-SHA256")
                digest = hashlib.sha256()
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{destination.name}.",
                    suffix=".part",
                    dir=destination.parent,
                    delete=False,
                ) as handle:
                    temporary = Path(handle.name)
                    size = 0
                    while chunk := response.read(1024 * 1024):
                        handle.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                actual = digest.hexdigest()
                if expected and not secrets.compare_digest(expected.lower(), actual):
                    raise CliError(
                        "Downloaded content failed SHA-256 verification",
                        kind="checksum_mismatch",
                        exit_code=5,
                    )
                os.replace(temporary, destination)
                temporary = None
                return {
                    "ok": True,
                    "output": str(destination),
                    "size_bytes": size,
                    "sha256": actual,
                    "server_sha256": expected,
                    "verified": bool(expected),
                    "request_id": response.headers.get("X-Request-ID"),
                }
        except urllib.error.HTTPError as exc:
            body = exc.read()
            decoded = _decode_response(body, exc.headers.get("Content-Type", ""))
            detail = decoded.get("detail") if isinstance(decoded, dict) else decoded
            raise CliError(
                str(detail or exc.reason),
                kind="http_error",
                status=exc.code,
                request_id=exc.headers.get("X-Request-ID"),
                detail=decoded,
                exit_code=3,
            ) from exc
        except CliError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise CliError(
                f"Research download failed: {reason}",
                kind="network_error",
                exit_code=4,
            ) from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


def _project_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True, help="Project UUID or slug")


def _add_json_option(parser: argparse.ArgumentParser, name: str, help_text: str) -> None:
    parser.add_argument(
        f"--{name}",
        help=f"{help_text}; inline JSON or @path/to/file.json",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bonfire-research",
        description="Headless, tenant-scoped Warehouse Research CLI",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL),
        help=f"Warehouse OS URL (default: ${BASE_URL_ENV} or {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--key-file",
        help=f"Read the key from a chmod 600 file instead of ${KEY_ENV}",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout seconds")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    parser.add_argument(
        "--allow-insecure-http",
        action="store_true",
        help="Allow remote plain HTTP (unsafe; intended only for controlled testing)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="group", required=True)

    sub.add_parser("whoami", help="Show the live identity and permissions behind this key")
    sub.add_parser("formats", help="Show supported custody, preview, and diff formats")

    project = sub.add_parser("project", help="Manage research projects").add_subparsers(
        dest="action", required=True
    )
    project.add_parser("list")
    create = project.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--slug")
    create.add_argument("--area")
    create.add_argument("--summary")
    create.add_argument(
        "--status", choices=("draft", "active", "review", "published", "archived")
    )
    _add_json_option(create, "metadata", "Project metadata object")
    show = project.add_parser("show")
    _project_option(show)
    commits = project.add_parser("commits")
    _project_option(commits)
    commits.add_argument("--limit", type=int, default=80)

    file_cmd = sub.add_parser("file", help="Upload, inspect, diff, and download files")
    file_sub = file_cmd.add_subparsers(dest="action", required=True)
    upload = file_sub.add_parser("upload")
    _project_option(upload)
    upload.add_argument("--file", required=True, dest="source")
    upload.add_argument("--path", dest="logical_path")
    upload.add_argument("--message", dest="commit_message")
    checksum = upload.add_mutually_exclusive_group()
    checksum.add_argument("--expected-sha256")
    checksum.add_argument("--no-checksum", action="store_true")
    versions = file_sub.add_parser("versions")
    _project_option(versions)
    versions.add_argument("--file", required=True, dest="file_ref")
    preview = file_sub.add_parser("preview")
    _project_option(preview)
    preview.add_argument("--file", required=True, dest="file_ref")
    preview.add_argument("--version", type=int)
    diff = file_sub.add_parser("diff")
    _project_option(diff)
    diff.add_argument("--file", required=True, dest="file_ref")
    diff.add_argument("--from", type=int, dest="from_version")
    diff.add_argument("--to", type=int, dest="to_version")
    download = file_sub.add_parser("download")
    _project_option(download)
    download.add_argument("--file", required=True, dest="file_ref")
    download.add_argument("--version", type=int)
    download.add_argument("--output", required=True)
    download.add_argument("--force", action="store_true")

    document = sub.add_parser(
        "document", help="Review, annotate, and ask grounded questions about a paper"
    ).add_subparsers(dest="action", required=True)
    document_review = document.add_parser("review")
    _project_option(document_review)
    document_review.add_argument("--file", required=True, dest="file_ref")
    document_review.add_argument("--version", type=int)
    document_annotate = document.add_parser("annotate")
    _project_option(document_annotate)
    document_annotate.add_argument("--file", required=True, dest="file_ref")
    document_annotate.add_argument("--version", type=int)
    _add_json_option(document_annotate, "anchor", "Text anchor object with quote/prefix/suffix")
    document_annotate.add_argument("--body", required=True)
    document_ask = document.add_parser("ask")
    _project_option(document_ask)
    document_ask.add_argument("--file", required=True, dest="file_ref")
    document_ask.add_argument("--version", type=int)
    document_ask.add_argument("--question", required=True)
    _add_json_option(document_ask, "anchor", "Optional selected-text anchor object")

    workflow = sub.add_parser("workflow").add_subparsers(dest="action", required=True)
    workflow_show = workflow.add_parser("show")
    _project_option(workflow_show)

    dmp = sub.add_parser("dmp").add_subparsers(dest="action", required=True)
    dmp_show = dmp.add_parser("show")
    _project_option(dmp_show)
    dmp_update = dmp.add_parser("update")
    _project_option(dmp_update)
    _add_json_option(dmp_update, "content", "DMP content object")
    dmp_update.add_argument("--question", "--research-question", dest="research_question")
    dmp_update.add_argument("--hypothesis")
    dmp_update.add_argument("--collection", "--data-collection", dest="data_collection")
    dmp_update.add_argument("--ethics", dest="ethics_legal_security")
    dmp_update.add_argument("--storage", dest="storage_preservation")
    dmp_update.add_argument("--sharing", dest="sharing_reuse")
    dmp_update.add_argument("--responsibilities")

    protocol = sub.add_parser("protocol").add_subparsers(dest="action", required=True)
    protocol_list = protocol.add_parser("list")
    _project_option(protocol_list)
    protocol_create = protocol.add_parser("create")
    _project_option(protocol_create)
    protocol_create.add_argument("--title", required=True)
    protocol_create.add_argument("--code")
    protocol_create.add_argument("--objective")
    protocol_create.add_argument("--status", choices=("draft", "locked", "retired"))
    _add_json_option(protocol_create, "specification", "Protocol specification object")

    run = sub.add_parser("run").add_subparsers(dest="action", required=True)
    run_list = run.add_parser("list")
    _project_option(run_list)
    run_start = run.add_parser("start")
    _project_option(run_start)
    run_start.add_argument("--title", required=True)
    run_start.add_argument("--code")
    run_start.add_argument("--protocol")
    run_start.add_argument(
        "--status", choices=("planned", "running", "completed", "failed", "cancelled")
    )
    _add_json_option(run_start, "inputs", "Run input object")
    _add_json_option(run_start, "environment", "Run environment object")
    _add_json_option(run_start, "observations", "Run observations object")
    run_start.add_argument("--deviation")
    run_update = run.add_parser("update")
    _project_option(run_update)
    run_update.add_argument("--run", required=True, dest="run_ref")
    run_update.add_argument(
        "--status", choices=("planned", "running", "completed", "failed", "cancelled")
    )
    _add_json_option(run_update, "inputs", "Run input object")
    _add_json_option(run_update, "environment", "Run environment object")
    _add_json_option(run_update, "observations", "Run observations object")
    run_update.add_argument("--deviation")

    claim = sub.add_parser("claim").add_subparsers(dest="action", required=True)
    claim_list = claim.add_parser("list")
    _project_option(claim_list)
    claim_create = claim.add_parser("create")
    _project_option(claim_create)
    claim_create.add_argument("--statement", required=True)
    claim_create.add_argument("--code")
    claim_create.add_argument("--confidence", type=float)
    claim_create.add_argument(
        "--status", choices=("draft", "submitted", "accepted", "changes_requested", "rejected")
    )
    _add_json_option(claim_create, "metadata", "Claim metadata object")

    evidence = sub.add_parser("evidence").add_subparsers(dest="action", required=True)
    evidence_link = evidence.add_parser("link")
    _project_option(evidence_link)
    evidence_link.add_argument("--claim", required=True)
    evidence_source = evidence_link.add_mutually_exclusive_group(required=True)
    evidence_source.add_argument("--file-version")
    evidence_source.add_argument("--run")
    evidence_link.add_argument(
        "--relation",
        choices=("supports", "contradicts", "method", "context"),
        default="supports",
    )
    evidence_link.add_argument("--note")

    review = sub.add_parser("review").add_subparsers(dest="action", required=True)
    review_list = review.add_parser("list")
    _project_option(review_list)
    review_submit = review.add_parser("submit")
    _project_option(review_submit)
    review_submit.add_argument(
        "--target-type", required=True, choices=("dmp", "protocol", "claim", "release")
    )
    review_submit.add_argument("--target", required=True)
    review_submit.add_argument(
        "--decision",
        required=True,
        choices=("comment", "approve", "changes_requested", "reject"),
    )
    review_submit.add_argument("--comment")
    _add_json_option(review_submit, "metadata", "Review metadata object")

    reproduce = sub.add_parser("reproduce").add_subparsers(dest="action", required=True)
    reproduce_check = reproduce.add_parser("check")
    _project_option(reproduce_check)

    execution = sub.add_parser("execution").add_subparsers(dest="action", required=True)
    execution.add_parser("runtimes")
    execution_list = execution.add_parser("list")
    _project_option(execution_list)
    execution_submit = execution.add_parser("submit")
    _project_option(execution_submit)
    execution_submit.add_argument("--entrypoint", required=True)
    execution_submit.add_argument("--title")
    execution_submit.add_argument("--runtime", default="python-3.13")
    _add_json_option(execution_submit, "arguments", "Argument array")
    _add_json_option(execution_submit, "inputs", "Pinned file-version ID array")
    _add_json_option(execution_submit, "limits", "Resource limit object")
    execution_submit.add_argument("--run")
    for action in ("show", "cancel", "retry"):
        item = execution.add_parser(action)
        _project_option(item)
        item.add_argument("--execution", required=True)
    execution_watch = execution.add_parser("watch")
    _project_option(execution_watch)
    execution_watch.add_argument("--execution", required=True)
    execution_watch.add_argument("--interval", type=float, default=2.0)
    execution_watch.add_argument("--wait-timeout", type=float, default=600.0)

    artifact = sub.add_parser("artifact").add_subparsers(dest="action", required=True)
    artifact_download = artifact.add_parser("download")
    _project_option(artifact_download)
    artifact_download.add_argument("--execution", required=True)
    artifact_download.add_argument("--artifact", required=True)
    artifact_download.add_argument("--output", required=True)
    artifact_download.add_argument("--force", action="store_true")
    artifact_promote = artifact.add_parser("promote")
    _project_option(artifact_promote)
    artifact_promote.add_argument("--execution", required=True)
    artifact_promote.add_argument("--artifact", required=True)
    artifact_promote.add_argument("--path")
    artifact_promote.add_argument("--message")

    release = sub.add_parser("release").add_subparsers(dest="action", required=True)
    release_list = release.add_parser("list")
    _project_option(release_list)
    release_create = release.add_parser("create")
    _project_option(release_create)
    release_create.add_argument("--title")
    release_create.add_argument("--description")
    release_create.add_argument(
        "--access", choices=("open", "embargoed", "restricted"), default="restricted"
    )
    release_create.add_argument("--license")
    release_create.add_argument("--embargo-until")
    release_show = release.add_parser("show")
    _project_option(release_show)
    release_show.add_argument("--release", required=True)
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _dispatch(client: ResearchClient, args: argparse.Namespace) -> object:
    group = args.group
    action = getattr(args, "action", None)
    if group == "whoami":
        return client.request("GET", "/api/auth/me")
    if group == "formats":
        return client.request("GET", "/api/research/formats")

    project_path = f"/api/research/projects/{_ref(getattr(args, 'project', ''))}"
    if group == "project":
        if action == "list":
            return client.request("GET", "/api/research/projects")
        if action == "create":
            payload: dict[str, object] = {"title": args.title}
            _field(payload, "slug", args.slug)
            _field(payload, "research_area", args.area)
            _field(payload, "summary", args.summary)
            _field(payload, "status", args.status)
            _field(payload, "metadata", _read_json(args.metadata, label="metadata", expected=dict))
            return client.request("POST", "/api/research/projects", payload)
        if action == "show":
            return client.request("GET", project_path)
        return client.request("GET", _with_query(f"{project_path}/commits", limit=args.limit))

    if group == "file":
        file_path = f"{project_path}/files/{_ref(getattr(args, 'file_ref', ''))}"
        if action == "upload":
            source = Path(args.source).expanduser().resolve()
            if not source.is_file():
                raise CliError(f"Upload source is not a regular file: {source}")
            expected = args.expected_sha256
            if expected is not None:
                expected = expected.strip().lower()
                if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
                    raise CliError("--expected-sha256 must contain 64 hexadecimal characters")
            elif not args.no_checksum:
                expected = _sha256(source)
            return client.upload(
                f"{project_path}/files",
                source,
                logical_path=args.logical_path,
                commit_message=args.commit_message,
                expected_sha256=expected,
            )
        if action == "versions":
            return client.request("GET", f"{file_path}/versions")
        if action == "preview":
            return client.request("GET", _with_query(f"{file_path}/preview", version=args.version))
        if action == "diff":
            return client.request(
                "GET",
                _with_query(
                    f"{file_path}/diff",
                    from_version=args.from_version,
                    to_version=args.to_version,
                ),
            )
        return client.download(
            _with_query(f"{file_path}/content", version=args.version),
            Path(args.output),
            force=args.force,
        )

    if group == "document":
        file_path = f"{project_path}/files/{_ref(args.file_ref)}"
        if action == "review":
            return client.request(
                "GET", _with_query(f"{file_path}/review", version=args.version)
            )
        anchor = _read_json(args.anchor, label="anchor", expected=dict)
        payload = {"version": args.version, "anchor": anchor}
        if action == "annotate":
            if anchor is None:
                raise CliError("--anchor is required for document annotate")
            payload["body"] = args.body
            return client.request("POST", f"{file_path}/annotations", payload)
        payload["question"] = args.question
        return client.request("POST", f"{file_path}/questions", payload)

    simple_lists = {
        ("workflow", "show"): "workflow",
        ("dmp", "show"): "dmp",
        ("protocol", "list"): "protocols",
        ("run", "list"): "runs",
        ("claim", "list"): "claims",
        ("review", "list"): "reviews",
        ("execution", "list"): "executions",
        ("release", "list"): "releases",
    }
    if (group, action) in simple_lists:
        return client.request("GET", f"{project_path}/{simple_lists[(group, action)]}")

    if group == "dmp":
        supplied = _read_json(args.content, label="content", expected=dict)
        payload = supplied or {}
        for name in (
            "research_question",
            "hypothesis",
            "data_collection",
            "ethics_legal_security",
            "storage_preservation",
            "sharing_reuse",
            "responsibilities",
        ):
            _field(payload, name, getattr(args, name))
        if not payload:
            raise CliError("dmp update requires --content or at least one DMP field")
        return client.request("PUT", f"{project_path}/dmp", {"content": payload})

    if group == "protocol":
        payload = {"title": args.title}
        _field(payload, "protocol_code", args.code)
        _field(payload, "objective", args.objective)
        _field(payload, "status", args.status)
        _field(
            payload,
            "specification",
            _read_json(args.specification, label="specification", expected=dict),
        )
        return client.request("POST", f"{project_path}/protocols", payload)

    if group == "run":
        payload = {}
        if action == "start":
            payload["title"] = args.title
            _field(payload, "run_code", args.code)
            _field(payload, "protocol_id", args.protocol)
        _field(payload, "status", args.status)
        for name in ("inputs", "environment", "observations"):
            _field(payload, name, _read_json(getattr(args, name), label=name, expected=dict))
        _field(payload, "deviation_note", args.deviation)
        if action == "start":
            return client.request("POST", f"{project_path}/runs", payload)
        return client.request("PATCH", f"{project_path}/runs/{_ref(args.run_ref)}", payload)

    if group == "claim":
        payload = {"statement": args.statement}
        _field(payload, "claim_code", args.code)
        _field(payload, "confidence", args.confidence)
        _field(payload, "status", args.status)
        _field(payload, "metadata", _read_json(args.metadata, label="metadata", expected=dict))
        return client.request("POST", f"{project_path}/claims", payload)

    if group == "evidence":
        payload = {"relation": args.relation}
        _field(payload, "file_version_id", args.file_version)
        _field(payload, "run_id", args.run)
        _field(payload, "note", args.note)
        return client.request(
            "POST", f"{project_path}/claims/{_ref(args.claim)}/evidence", payload
        )

    if group == "review":
        payload = {
            "target_type": args.target_type,
            "target_id": args.target,
            "decision": args.decision,
        }
        _field(payload, "comment", args.comment)
        _field(payload, "metadata", _read_json(args.metadata, label="metadata", expected=dict))
        return client.request("POST", f"{project_path}/reviews", payload)

    if group == "reproduce":
        return client.request("POST", f"{project_path}/reproducibility-checks", {})

    if group == "execution":
        if action == "runtimes":
            return client.request("GET", "/api/research/execution-runtimes")
        execution_path = f"{project_path}/executions/{_ref(getattr(args, 'execution', ''))}"
        if action == "submit":
            payload = {"entrypoint": args.entrypoint, "runtime": args.runtime}
            _field(payload, "title", args.title)
            _field(payload, "run_id", args.run)
            _field(
                payload,
                "arguments",
                _read_json(args.arguments, label="arguments", expected=list),
            )
            _field(
                payload,
                "input_file_version_ids",
                _read_json(args.inputs, label="inputs", expected=list),
            )
            _field(
                payload,
                "resource_limits",
                _read_json(args.limits, label="limits", expected=dict),
            )
            return client.request("POST", f"{project_path}/executions", payload)
        if action == "show":
            return client.request("GET", execution_path)
        if action == "watch":
            if args.interval <= 0 or args.wait_timeout <= 0:
                raise CliError("watch interval and timeout must be greater than zero")
            started = time.monotonic()
            while True:
                result = client.request("GET", execution_path)
                execution_value = result.get("execution") if isinstance(result, dict) else None
                status_value = (
                    str(execution_value.get("status"))
                    if isinstance(execution_value, dict)
                    else ""
                )
                if status_value in TERMINAL_EXECUTION_STATUSES:
                    if isinstance(result, dict):
                        result["watch"] = {
                            "terminal": True,
                            "elapsed_seconds": round(time.monotonic() - started, 3),
                        }
                    return result
                if time.monotonic() - started >= args.wait_timeout:
                    raise CliError(
                        f"Execution did not finish within {args.wait_timeout:g} seconds",
                        kind="watch_timeout",
                        detail=result,
                        exit_code=6,
                    )
                time.sleep(args.interval)
        return client.request("POST", f"{execution_path}/{action}", {})

    if group == "artifact":
        artifact_path = (
            f"{project_path}/executions/{_ref(args.execution)}"
            f"/artifacts/{_ref(args.artifact)}"
        )
        if action == "download":
            return client.download(
                f"{artifact_path}/content", Path(args.output), force=args.force
            )
        payload = {}
        _field(payload, "logical_path", args.path)
        _field(payload, "commit_message", args.message)
        return client.request("POST", f"{artifact_path}/promote", payload)

    if group == "release":
        if action == "create":
            payload = {"access_level": args.access}
            _field(payload, "title", args.title)
            _field(payload, "description", args.description)
            _field(payload, "license", args.license)
            _field(payload, "embargo_until", args.embargo_until)
            return client.request("POST", f"{project_path}/releases", payload)
        return client.request("GET", f"{project_path}/releases/{_ref(args.release)}")
    raise CliError("Unsupported command")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.timeout <= 0:
            raise CliError("--timeout must be greater than zero")
        base_url = _validate_base_url(
            args.base_url, allow_insecure_http=args.allow_insecure_http
        )
        key = _read_key(args.key_file)
        result = _dispatch(ResearchClient(base_url, key, args.timeout), args)
        _print_json(result, compact=args.compact)
        if (
            args.group == "execution"
            and getattr(args, "action", None) == "watch"
            and isinstance(result, dict)
            and isinstance(result.get("execution"), dict)
            and result["execution"].get("status") != "succeeded"
        ):
            return 5
        return 0
    except CliError as exc:
        _print_json(exc.payload(), compact=args.compact, stream=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        _print_json(
            {"ok": False, "error": {"type": "interrupted", "message": "Interrupted"}},
            compact=args.compact,
            stream=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
