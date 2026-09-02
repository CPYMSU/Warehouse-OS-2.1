#!/usr/bin/env python3
"""Publish linked GitHub repositories as governed Warehouse OS workspace releases.

This helper is intentionally runner-side only. It never needs host SSH, a Docker
socket, or database credentials: every deployment goes through the workspace
HTTPS API with the workspace's own ``wak_`` credential.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ACTIVE_UPLOAD_RE = re.compile(r'"upload_id"\s*:\s*"([0-9a-fA-F-]{36})"')
RUNTIME_TYPES = frozenset(
    {"auto", "static", "web", "api", "worker", "agent", "container", "compose"}
)
FAILURE_STATES = frozenset({"failed", "rolled_back", "cancelled", "blocked"})


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 900,
) -> str:
    completed = subprocess.run(
        argv,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "command failed").strip()
        raise RuntimeError(f"{argv[0]} failed: {message[-1800:]}")
    return completed.stdout


def _json_output(raw: str, *, source: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{source} did not return JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{source} returned a non-object JSON value")
    return value


def _load_links(raw: str) -> list[dict[str, Any]]:
    if not raw.strip():
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("WAREHOUSE_ASSET_LINKS_JSON is not valid JSON") from exc
    if isinstance(payload, dict):
        payload = payload.get("links")
    if not isinstance(payload, list):
        raise RuntimeError("WAREHOUSE_ASSET_LINKS_JSON must be a list or {\"links\": [...]}\")")

    links: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise RuntimeError(f"link #{index + 1} must be a JSON object")
        if item.get("enabled") is False:
            continue
        repository = str(item.get("repository") or "").strip()
        if not REPOSITORY_RE.fullmatch(repository):
            raise RuntimeError(f"link #{index + 1} has an invalid repository: {repository!r}")
        source_path = str(item.get("source_path") or "").strip().strip("/")
        if source_path:
            parsed_source = PurePosixPath(source_path)
            if parsed_source.is_absolute() or ".." in parsed_source.parts:
                raise RuntimeError(f"link {repository} has unsafe source_path={source_path!r}")
        workspace_key = str(item.get("workspace_key") or "").strip()
        if not workspace_key.startswith("wak_"):
            raise RuntimeError(f"link {repository} requires a wak_ workspace_key")
        runtime_type = str(item.get("runtime_type") or "auto").strip().lower()
        if runtime_type not in RUNTIME_TYPES:
            raise RuntimeError(
                f"link {repository} has unsupported runtime_type={runtime_type!r}"
            )
        try:
            timeout_seconds = int(item.get("timeout_seconds") or 3600)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"link {repository} has an invalid timeout_seconds") from exc
        if not 60 <= timeout_seconds <= 7200:
            raise RuntimeError(
                f"link {repository} timeout_seconds must be between 60 and 7200"
            )
        links.append(
            {
                "repository": repository,
                "ref": str(item.get("ref") or "main").strip(),
                "source_path": source_path,
                "workspace_key": workspace_key,
                "runtime_type": runtime_type,
                "component": str(item.get("component") or "").strip(),
                "activate": item.get("activate") is not False,
                "timeout_seconds": timeout_seconds,
            }
        )
    return links


def _git_environment(token: str) -> dict[str, str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    token = token.strip()
    if token:
        env.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.extraHeader",
                "GIT_CONFIG_VALUE_0": f"Authorization: Bearer {token}",
            }
        )
    return env


def _workspace_environment(base_url: str, workspace_key: str) -> dict[str, str]:
    return {
        **os.environ,
        "WAREHOUSE_BASE_URL": base_url.rstrip("/"),
        "WAREHOUSE_WORKSPACE_KEY": workspace_key,
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def _workspace_request(
    env: dict[str, str],
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
) -> dict[str, Any]:
    base_url = str(env.get("WAREHOUSE_BASE_URL") or "").rstrip("/")
    workspace_key = str(env.get("WAREHOUSE_WORKSPACE_KEY") or "")
    if not base_url or not workspace_key.startswith("wak_"):
        raise RuntimeError("workspace API environment is incomplete")
    body = None
    headers = {
        "Authorization": "Bearer " + workspace_key,
        "Accept": "application/json",
        "User-Agent": "Warehouse-MacRunner-DigitalAssetPublisher/1.1",
    }
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(base_url + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return _json_output(response.read().decode("utf-8"), source=f"{method} {path}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"workspace API {method} {path} returned HTTP {exc.code}: {raw[-1200:]}") from exc


def _download_cli(base_url: str, target: Path) -> None:
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/digital-assets/cli",
        headers={"User-Agent": "Warehouse-MacRunner-DigitalAssetPublisher/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())
    except Exception as exc:
        raise RuntimeError("failed to download the Warehouse digital-asset CLI") from exc


def _source_id(item: dict[str, Any]) -> str:
    return str(item.get("uuid") or item.get("source_version_id") or item.get("id") or "")


def _find_source_for_version(
    python: str,
    cli: Path,
    env: dict[str, str],
    version_no: str,
) -> str | None:
    data = _json_output(
        _run([python, str(cli), "source", "list"], env=env, timeout=120),
        source="source list",
    )
    sources = data.get("sources")
    if not isinstance(sources, list):
        return None
    for item in sources:
        if not isinstance(item, dict):
            continue
        if str(item.get("version_no") or "") != version_no:
            continue
        reference = _source_id(item)
        if reference:
            return reference
    return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _build_deterministic_archive(
    checkout: Path,
    *,
    treeish: str,
    version_no: str,
) -> Path:
    archive = checkout.parent / f"{version_no}.stable.tar.gz"
    raw_tar = checkout.parent / f"{version_no}.stable.tar"
    temporary = checkout.parent / f"{version_no}.stable.tar.gz.tmp"
    _run(
        ["git", "archive", "--format=tar", f"--output={raw_tar}", treeish],
        cwd=checkout,
        timeout=300,
    )
    try:
        with raw_tar.open("rb") as source, temporary.open("wb") as target:
            with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    compressed.write(chunk)
        temporary.replace(archive)
    finally:
        raw_tar.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
    return archive


def _recover_conflicting_source_upload(
    env: dict[str, str],
    *,
    error: RuntimeError,
    archive: Path,
    version_no: str,
) -> bool:
    message = str(error)
    if "source_version_upload_already_active" not in message:
        return False
    match = ACTIVE_UPLOAD_RE.search(message)
    if match is None:
        return False
    upload_id = match.group(1)
    observed = _workspace_request(
        env,
        "GET",
        f"/api/workspaces/v1/source-uploads/{upload_id}",
    )
    if str(observed.get("version_no") or "") != version_no:
        return False
    status = str(observed.get("status") or "")
    if status not in {"created", "uploading"}:
        return False
    local_size = archive.stat().st_size
    local_sha256 = _file_sha256(archive)
    remote_size = int(observed.get("size_bytes") or 0)
    remote_sha256 = str(observed.get("sha256") or "")
    if remote_size == local_size and remote_sha256 == local_sha256:
        return False
    print(
        f"cancelling stale source upload {upload_id} for {version_no}: "
        f"remote={remote_size}/{remote_sha256[:12]} local={local_size}/{local_sha256[:12]}",
        flush=True,
    )
    _workspace_request(
        env,
        "POST",
        f"/api/workspaces/v1/source-uploads/{upload_id}/cancel",
        payload={},
    )
    return True


def _push_source(
    python: str,
    cli: Path,
    env: dict[str, str],
    checkout: Path,
    commit: str,
    component: str,
    source_path: str,
    version_no: str,
) -> str:
    treeish = commit
    if source_path:
        source_root = (checkout / source_path).resolve()
        try:
            source_root.relative_to(checkout.resolve())
        except ValueError as exc:
            raise RuntimeError(f"source_path escaped checkout: {source_path!r}") from exc
        if not source_root.is_dir():
            raise RuntimeError(f"source_path does not exist: {source_path!r}")
        treeish = f"{commit}:{source_path}"
    archive = _build_deterministic_archive(
        checkout,
        treeish=treeish,
        version_no=version_no,
    )
    argv = [
        python,
        str(cli),
        "source",
        "push",
        str(archive),
        "--version",
        version_no,
    ]
    if component:
        argv.extend(["--component", component])
    try:
        raw = _run(argv, env=env, timeout=1200)
    except RuntimeError as exc:
        if not _recover_conflicting_source_upload(
            env,
            error=exc,
            archive=archive,
            version_no=version_no,
        ):
            raise
        raw = _run(argv, env=env, timeout=1200)
    data = _json_output(raw, source="source push")
    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    reference = _source_id(source)
    if not reference:
        reference = str(data.get("source_version_id") or "")
    if not reference:
        raise RuntimeError("source push did not return a source version id")
    return reference


def _create_release(
    python: str,
    cli: Path,
    env: dict[str, str],
    *,
    repository: str,
    source_path: str,
    commit: str,
    source_id: str,
    runtime_type: str,
    component: str,
) -> str:
    argv = [
        python,
        str(cli),
        "release",
        "run",
        "--source",
        source_id,
        "--type",
        runtime_type,
        "--idempotency-key",
        "github:" + hashlib.sha256(
            f"{repository}:{source_path}:{commit}:{runtime_type}:{component}".encode("utf-8")
        ).hexdigest(),
        "--no-wait",
    ]
    if component:
        argv.extend(["--component", component])
    data = _json_output(_run(argv, env=env, timeout=180), source="release run")
    release = data.get("release") if isinstance(data.get("release"), dict) else {}
    reference = str(release.get("uuid") or release.get("id") or "")
    if not reference:
        raise RuntimeError("release run did not return a release id")
    return reference


def _wait_for_release(
    python: str,
    cli: Path,
    env: dict[str, str],
    release_id: str,
    *,
    activate: bool,
    timeout_seconds: int,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    previous_state = ""
    activation_sent = False
    while time.monotonic() < deadline:
        data = _json_output(
            _run(
                [python, str(cli), "release", "status", release_id],
                env=env,
                timeout=120,
            ),
            source="release status",
        )
        release = data.get("release") if isinstance(data.get("release"), dict) else {}
        state = str(release.get("state") or "")
        if state != previous_state:
            print(f"release {release_id}: {state or 'unknown'}", flush=True)
            previous_state = state
        if state == "verified":
            return state
        if state in FAILURE_STATES:
            error = release.get("last_error")
            raise RuntimeError(
                f"release {release_id} ended in {state}: "
                + json.dumps(error or {}, ensure_ascii=False, default=str)
            )
        if state == "awaiting_activation":
            if not activate:
                return state
            if not activation_sent:
                _run(
                    [python, str(cli), "release", "activate", release_id],
                    env=env,
                    timeout=180,
                )
                activation_sent = True
        elif state:
            # The Runtime Controller remains authoritative. This idempotent nudge
            # simply avoids waiting for its next poll when the Mac runner is alive.
            _run(
                [python, str(cli), "release", "resume", release_id],
                env=env,
                timeout=180,
            )
        time.sleep(2)
    raise RuntimeError(f"release {release_id} exceeded {timeout_seconds} seconds")


def _publish_link(
    link: dict[str, Any],
    *,
    base_url: str,
    github_token: str,
    python: str,
    cli: Path,
    temp_root: Path,
) -> dict[str, str]:
    repository = link["repository"]
    ref = link["ref"]
    source_path = str(link.get("source_path") or "")
    checkout = temp_root / repository.replace("/", "__")
    url = f"https://github.com/{repository}.git"
    print(f"checking {repository}@{ref}", flush=True)
    _run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            ref,
            "--single-branch",
            "--no-tags",
            url,
            str(checkout),
        ],
        env=_git_environment(github_token),
        timeout=600,
    )
    commit = _run(["git", "rev-parse", "HEAD"], cwd=checkout, timeout=30).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError(f"{repository} returned an invalid commit id")

    version_no = (
        commit
        if not source_path
        else f"{commit}-{hashlib.sha256(source_path.encode('utf-8')).hexdigest()[:12]}"
    )
    workspace_env = _workspace_environment(base_url, link["workspace_key"])
    source_id = _find_source_for_version(python, cli, workspace_env, version_no)
    source_reused = source_id is not None
    if source_id is None:
        source_id = _push_source(
            python,
            cli,
            workspace_env,
            checkout,
            commit,
            link["component"],
            source_path,
            version_no,
        )

    release_id = _create_release(
        python,
        cli,
        workspace_env,
        repository=repository,
        source_path=source_path,
        commit=commit,
        source_id=source_id,
        runtime_type=link["runtime_type"],
        component=link["component"],
    )
    state = _wait_for_release(
        python,
        cli,
        workspace_env,
        release_id,
        activate=bool(link["activate"]),
        timeout_seconds=int(link["timeout_seconds"]),
    )
    return {
        "repository": repository,
        "ref": ref,
        "source_path": source_path,
        "commit": commit,
        "source_version": version_no,
        "source_version_id": source_id,
        "source": "reused" if source_reused else "uploaded",
        "release_id": release_id,
        "release_state": state,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish linked GitHub repositories into Warehouse digital-asset workspaces."
    )
    parser.add_argument(
        "--repository",
        help="Publish only one owner/repository entry from WAREHOUSE_ASSET_LINKS_JSON.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate the link registry without cloning or deploying.",
    )
    args = parser.parse_args()

    base_url = (os.environ.get("WAREHOUSE_BASE_URL") or "https://bonfirework.org").strip()
    links = _load_links(os.environ.get("WAREHOUSE_ASSET_LINKS_JSON") or "")
    selected = (args.repository or os.environ.get("WAREHOUSE_ASSET_REPOSITORY") or "").strip()
    if selected:
        links = [link for link in links if link["repository"] == selected]
        if not links:
            raise SystemExit(f"repository {selected!r} is not configured in WAREHOUSE_ASSET_LINKS_JSON")
    if args.validate_config:
        print(json.dumps({"ok": True, "links": len(links)}, ensure_ascii=False))
        return
    if not links:
        print("No linked digital assets are configured; nothing to publish.")
        return

    github_token = os.environ.get("WAREHOUSE_ASSET_GITHUB_TOKEN") or ""
    python = sys.executable or "python3"
    failures: list[dict[str, str]] = []
    results: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="warehouse-asset-publish-") as temporary:
        temp_root = Path(temporary)
        cli = temp_root / "dam.py"
        _download_cli(base_url, cli)
        for link in links:
            try:
                results.append(
                    _publish_link(
                        link,
                        base_url=base_url,
                        github_token=github_token,
                        python=python,
                        cli=cli,
                        temp_root=temp_root,
                    )
                )
            except Exception as exc:
                failures.append(
                    {
                        "repository": str(link["repository"]),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                print(
                    f"publish failed for {link['repository']}: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

    print(json.dumps({"published": results, "failures": failures}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
