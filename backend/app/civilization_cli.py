#!/usr/bin/env python3
"""Dependency-free CLI for the tenant-scoped Civilization publishing API."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "1.0.1"
DEFAULT_BASE_URL = "https://bonfirework.org"
KEY_ENV = "WAREHOUSE_CIVILIZATION_KEY"
BASE_URL_ENV = "WAREHOUSE_BASE_URL"
CLI_COMMANDS = (
    "whoami",
    "templates",
    "post list|show|create|delete",
    "draft save",
    "preview",
    "publish",
    "share enable|disable",
    "revisions",
    "restore",
    "lens upsert",
)


class CliError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, detail: object = None) -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail

    def payload(self) -> dict[str, object]:
        data: dict[str, object] = {"type": "cli_error", "message": str(self)}
        if self.status is not None:
            data["status"] = self.status
        if self.detail is not None:
            data["detail"] = self.detail
        return {"ok": False, "error": data}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _ref(value: object) -> str:
    return urllib.parse.quote(str(value), safe="")


def _read_json(value: str | None, *, label: str) -> dict[str, object] | None:
    if value is None:
        return None
    source = value
    if value.startswith("@"):
        try:
            source = Path(value[1:]).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(f"Cannot read {label}: {exc}") from exc
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise CliError(f"Invalid {label} JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise CliError(f"{label} must be a JSON object")
    return parsed


def _read_array(value: str | None, *, label: str) -> list[object] | None:
    if value is None:
        return None
    source = value
    if value.startswith("@"):
        try:
            source = Path(value[1:]).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(f"Cannot read {label}: {exc}") from exc
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise CliError(f"Invalid {label} JSON: {exc.msg}") from exc
    if not isinstance(parsed, list):
        raise CliError(f"{label} must be a JSON array")
    return parsed


def _key(args: argparse.Namespace) -> str:
    if args.key_file:
        path = Path(args.key_file).expanduser()
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o077:
                raise CliError("Key file must not be readable by group or others (chmod 600)")
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise CliError(f"Cannot read key file: {exc}") from exc
    else:
        value = os.environ.get(KEY_ENV, "").strip()
    if not value.startswith("wsk_") or any(character.isspace() for character in value):
        raise CliError(f"Set ${KEY_ENV} or use --key-file with a valid Runtime API Key")
    return value


class Client:
    def __init__(self, base_url: str, key: str, *, timeout: float, allow_http: bool) -> None:
        self.base_url = base_url.rstrip("/")
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise CliError("--base-url must be an absolute HTTP(S) URL")
        if (
            parsed.scheme != "https"
            and not allow_http
            and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        ):
            raise CliError("Remote plain HTTP is refused; use HTTPS")
        self.key = key
        self.timeout = timeout
        self.opener = urllib.request.build_opener(
            _NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
        )

    def request(self, method: str, path: str, payload: object = None) -> object:
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.key}",
                "Accept": "application/json",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read()
                return json.loads(body.decode("utf-8")) if body else {"ok": True}
        except urllib.error.HTTPError as exc:
            body = exc.read()
            try:
                detail = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail = body.decode("utf-8", errors="replace") or exc.reason
            raise CliError(
                str(detail.get("detail") if isinstance(detail, dict) else detail),
                status=exc.code,
                detail=detail,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise CliError(f"Civilization request failed: {getattr(exc, 'reason', exc)}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bonfire-civilization",
        description="Edit content inside the locked Swiss B Civilization layout",
    )
    parser.add_argument("--base-url", default=os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL))
    parser.add_argument("--key-file")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--allow-insecure-http", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    groups = parser.add_subparsers(dest="group", required=True)
    groups.add_parser("whoami")
    groups.add_parser("templates")

    post = groups.add_parser("post").add_subparsers(dest="action", required=True)
    post.add_parser("list")
    show = post.add_parser("show")
    show.add_argument("--post", required=True)
    delete = post.add_parser("delete")
    delete.add_argument("--post", required=True)
    create = post.add_parser("create")
    create.add_argument(
        "--domain",
        default="judgement",
        choices=("judgement", "technology", "organization", "time", "ethics"),
    )
    create.add_argument("--locale", default="zh")
    create.add_argument("--content", required=True, help="Inline JSON or @content.json")
    create.add_argument("--lenses", help="Inline JSON object with a lenses array or @file")
    create.add_argument("--relations", help="Inline JSON array or @relations.json")
    create.add_argument("--publish", action="store_true")

    draft = groups.add_parser("draft").add_subparsers(dest="action", required=True)
    save = draft.add_parser("save")
    save.add_argument("--post", required=True)
    save.add_argument("--revision", required=True, type=int)
    save.add_argument(
        "--domain", choices=("judgement", "technology", "organization", "time", "ethics")
    )
    save.add_argument("--locale", default="zh")
    save.add_argument("--content", required=True, help="Inline JSON or @content.json")
    save.add_argument("--relations", help="Inline JSON array or @relations.json")

    preview = groups.add_parser("preview")
    preview.add_argument("--post", required=True)
    publish = groups.add_parser("publish")
    publish.add_argument("--post", required=True)
    publish.add_argument("--revision", required=True, type=int)
    share = groups.add_parser("share").add_subparsers(dest="action", required=True)
    for share_action in ("enable", "disable"):
        share_parser = share.add_parser(share_action)
        share_parser.add_argument("--post", required=True)
        share_parser.add_argument("--revision", required=True, type=int)
    revisions = groups.add_parser("revisions")
    revisions.add_argument("--post", required=True)
    restore = groups.add_parser("restore")
    restore.add_argument("--post", required=True)
    restore.add_argument("--source-revision", required=True, type=int)
    restore.add_argument("--revision", required=True, type=int)

    lens = groups.add_parser("lens").add_subparsers(dest="action", required=True)
    upsert = lens.add_parser("upsert")
    upsert.add_argument("--post", required=True)
    upsert.add_argument("--index", required=True, type=int, help="Zero-based lens index")
    upsert.add_argument("--revision", required=True, type=int)
    upsert.add_argument("--name", required=True)
    upsert.add_argument("--text", required=True)
    upsert.add_argument("--locale", default="zh")
    return parser


def dispatch(client: Client, args: argparse.Namespace) -> object:
    if args.group == "whoami":
        return client.request("GET", "/api/auth/me")
    if args.group == "templates":
        return client.request("GET", "/api/civilization/templates")
    if args.group == "post":
        if args.action == "list":
            return client.request("GET", "/api/civilization/thoughts")
        if args.action == "show":
            return client.request("GET", f"/api/civilization/thoughts/{_ref(args.post)}")
        if args.action == "delete":
            return client.request("DELETE", f"/api/civilization/thoughts/{_ref(args.post)}")
        content = _read_json(args.content, label="content")
        payload: dict[str, object] = {
            "domain": args.domain,
            "locale": args.locale,
            "content": content,
            "publish": args.publish,
        }
        lenses = _read_json(args.lenses, label="lenses")
        if lenses is not None:
            payload["lenses"] = lenses.get("lenses", [])
        relations = _read_array(args.relations, label="relations")
        if relations is not None:
            payload["relations"] = relations
        return client.request("POST", "/api/civilization/thoughts", payload)
    post_path = f"/api/civilization/thoughts/{_ref(args.post)}"
    if args.group == "draft":
        payload = {
            "expected_revision": args.revision,
            "locale": args.locale,
            "content": _read_json(args.content, label="content"),
        }
        if args.domain:
            payload["domain"] = args.domain
        relations = _read_array(args.relations, label="relations")
        if relations is not None:
            payload["relations"] = relations
        return client.request("PATCH", f"{post_path}/draft", payload)
    if args.group == "preview":
        return client.request("GET", f"{post_path}/preview")
    if args.group == "publish":
        return client.request("POST", f"{post_path}/publish", {"expected_revision": args.revision})
    if args.group == "share":
        return client.request(
            "PUT",
            f"{post_path}/share",
            {"expected_revision": args.revision, "enabled": args.action == "enable"},
        )
    if args.group == "revisions":
        return client.request("GET", f"{post_path}/revisions")
    if args.group == "restore":
        return client.request(
            "POST",
            f"{post_path}/revisions/{args.source_revision}/restore",
            {"expected_revision": args.revision},
        )
    if args.group == "lens":
        return client.request(
            "PUT",
            f"{post_path}/lenses/{args.index}",
            {
                "expected_revision": args.revision,
                "locale": args.locale,
                "name": args.name,
                "text": args.text,
            },
        )
    raise CliError("Unsupported Civilization command")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        client = Client(
            args.base_url,
            _key(args),
            timeout=args.timeout,
            allow_http=args.allow_insecure_http,
        )
        result = dispatch(client, args)
        json.dump(result, sys.stdout, ensure_ascii=False, indent=None if args.compact else 2)
        sys.stdout.write("\n")
        return 0
    except CliError as exc:
        json.dump(exc.payload(), sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 3 if exc.status else 2


if __name__ == "__main__":
    raise SystemExit(main())
