#!/usr/bin/env python3
"""Resolve a Git-backed digital-asset registry, then invoke the Mac publisher.

The registry contains no Warehouse credentials. Each entry names a
``workspace_key_ref``; the corresponding ``wak_`` value comes either from the
``WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON`` Actions secret or, on the governed Mac
mini runner, from a local owner-only JSON file. Private GitHub reads may use an
Actions token when supplied or the Mac mini's repository-scoped read-only SSH
Deploy Key. Secret values are never written back to Git or printed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
KEY_REF_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
DEFAULT_REGISTRY = "CPYMSU/registry"
DEFAULT_REF = "main"
DEFAULT_PATH = "registry.json"
DEFAULT_WORKSPACE_KEYS_FILE = Path(
    "/Users/peiyuan/Server/bonfirework/secrets/digital-asset-workspace-keys.json"
)
DEFAULT_REGISTRY_SSH_KEY = Path(
    "/Users/peiyuan/Server/bonfirework/secrets/registry-read-ed25519"
)
DEFAULT_GITHUB_KNOWN_HOSTS = Path("/Users/peiyuan/.ssh/known_hosts")


def _run(argv: list[str], *, env: dict[str, str] | None = None, timeout: int = 300) -> None:
    completed = subprocess.run(
        argv,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "command failed").strip()
        raise RuntimeError(f"{argv[0]} failed: {message[-1800:]}")


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


def _protected_file(path: Path, *, label: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"{label} is unavailable")
    metadata = path.stat()
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise RuntimeError(f"{label} must not be group/world accessible")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise RuntimeError(f"{label} must be owned by the runner user")


def _ssh_git_environment(key_path: Path) -> dict[str, str]:
    _protected_file(key_path, label="Registry SSH Deploy Key")
    known_hosts = Path(
        os.environ.get("WAREHOUSE_ASSET_GITHUB_KNOWN_HOSTS") or DEFAULT_GITHUB_KNOWN_HOSTS
    ).expanduser()
    if not known_hosts.is_file():
        raise RuntimeError("GitHub known_hosts file is unavailable")
    command = " ".join(
        [
            "ssh",
            "-F", "/dev/null",
            "-i", shlex.quote(str(key_path)),
            "-o", "BatchMode=yes",
            "-o", "IdentitiesOnly=yes",
            "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={shlex.quote(str(known_hosts))}",
            "-o", "ConnectTimeout=15",
        ]
    )
    return {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_SSH_COMMAND": command,
    }


def _git_access(repository: str, token: str) -> tuple[str, dict[str, str]]:
    if token.strip():
        return f"https://github.com/{repository}.git", _git_environment(token)
    configured = os.environ.get("WAREHOUSE_ASSET_REGISTRY_SSH_KEY") or ""
    key_path = Path(configured).expanduser() if configured.strip() else DEFAULT_REGISTRY_SSH_KEY
    if key_path.is_file():
        return f"git@github.com:{repository}.git", _ssh_git_environment(key_path)
    return f"https://github.com/{repository}.git", _git_environment("")


def _load_json_object(raw: str, *, source: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{source} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{source} must be a JSON object")
    return value


def _workspace_key_file() -> Path:
    configured = os.environ.get("WAREHOUSE_ASSET_WORKSPACE_KEYS_FILE") or ""
    path = Path(configured).expanduser() if configured.strip() else DEFAULT_WORKSPACE_KEYS_FILE
    if not path.is_absolute():
        raise RuntimeError("WAREHOUSE_ASSET_WORKSPACE_KEYS_FILE must be an absolute path")
    return path


def _workspace_keys() -> dict[str, str]:
    raw = (os.environ.get("WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON") or "").strip()
    source = "WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON"
    if not raw:
        path = _workspace_key_file()
        _protected_file(path, label="protected Mac workspace-key file")
        raw = path.read_text(encoding="utf-8")
        source = "protected Mac workspace-key file"

    values = _load_json_object(raw, source=source)
    keys: dict[str, str] = {}
    for raw_name, raw_value in values.items():
        name = str(raw_name).strip()
        value = str(raw_value).strip()
        if not KEY_REF_RE.fullmatch(name):
            raise RuntimeError(f"invalid workspace key reference: {name!r}")
        if not value.startswith("wak_"):
            raise RuntimeError(f"workspace key reference {name!r} does not contain a wak_ key")
        keys[name] = value
    return keys


def _registry_links(path: Path, workspace_keys: dict[str, str]) -> list[dict[str, Any]]:
    payload = _load_json_object(path.read_text(encoding="utf-8"), source=str(path))
    schema = str(payload.get("schema") or "").strip()
    if schema and schema != "warehouse.digital-asset-registry.v1":
        raise RuntimeError(f"unsupported registry schema: {schema!r}")
    links = payload.get("links")
    if not isinstance(links, list):
        raise RuntimeError("registry.json must contain a links array")

    resolved: list[dict[str, Any]] = []
    seen_sources: set[tuple[str, str]] = set()
    for index, raw in enumerate(links, start=1):
        if not isinstance(raw, dict):
            raise RuntimeError(f"registry link #{index} must be an object")
        if raw.get("enabled") is False:
            continue
        if raw.get("workspace_key"):
            raise RuntimeError(
                f"registry link #{index} contains workspace_key; commit only workspace_key_ref"
            )
        repository = str(raw.get("repository") or "").strip()
        if not REPOSITORY_RE.fullmatch(repository):
            raise RuntimeError(f"registry link #{index} has invalid repository {repository!r}")
        source_path = str(raw.get("source_path") or "").strip().strip("/")
        source_identity = (repository, source_path)
        if source_identity in seen_sources:
            raise RuntimeError(
                f"registry contains duplicate source {repository!r} path {source_path!r}"
            )
        seen_sources.add(source_identity)
        key_ref = str(raw.get("workspace_key_ref") or "").strip()
        if not KEY_REF_RE.fullmatch(key_ref):
            raise RuntimeError(f"registry link {repository} requires workspace_key_ref")
        workspace_key = workspace_keys.get(key_ref)
        if workspace_key is None:
            raise RuntimeError(
                f"registry link {repository} references missing workspace key {key_ref!r}"
            )
        item = dict(raw)
        item.pop("workspace_key_ref", None)
        item["workspace_key"] = workspace_key
        resolved.append(item)
    return resolved


def _checkout_registry(target: Path) -> Path:
    repository = (
        os.environ.get("WAREHOUSE_ASSET_REGISTRY_REPOSITORY") or DEFAULT_REGISTRY
    ).strip()
    ref = (os.environ.get("WAREHOUSE_ASSET_REGISTRY_REF") or DEFAULT_REF).strip()
    relative_path = (os.environ.get("WAREHOUSE_ASSET_REGISTRY_PATH") or DEFAULT_PATH).strip()
    token = os.environ.get("WAREHOUSE_ASSET_GITHUB_TOKEN") or ""
    if not REPOSITORY_RE.fullmatch(repository):
        raise RuntimeError(f"invalid registry repository: {repository!r}")
    if not ref:
        raise RuntimeError("WAREHOUSE_ASSET_REGISTRY_REF cannot be empty")
    if not relative_path or relative_path.startswith("/") or ".." in Path(relative_path).parts:
        raise RuntimeError("WAREHOUSE_ASSET_REGISTRY_PATH must be a safe relative path")

    checkout = target / "registry"
    url, git_env = _git_access(repository, token)
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
        env=git_env,
        timeout=300,
    )
    registry_path = (checkout / relative_path).resolve()
    try:
        registry_path.relative_to(checkout.resolve())
    except ValueError as exc:
        raise RuntimeError("registry path escaped the checkout") from exc
    if not registry_path.is_file():
        raise RuntimeError(f"registry file not found: {relative_path}")
    return registry_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve the dedicated digital-asset registry and publish from Mac mini."
    )
    parser.add_argument("--repository", help="Publish only one owner/repository binding.")
    parser.add_argument("--validate-config", action="store_true")
    args = parser.parse_args()

    workspace_keys = _workspace_keys()
    with tempfile.TemporaryDirectory(prefix="warehouse-asset-registry-") as temporary:
        registry_path = _checkout_registry(Path(temporary))
        links = _registry_links(registry_path, workspace_keys)

    selected = (args.repository or os.environ.get("WAREHOUSE_ASSET_REPOSITORY") or "").strip()
    if selected and not any(str(link.get("repository")) == selected for link in links):
        raise SystemExit(f"repository {selected!r} is not configured in the digital-asset registry")

    child_env = {
        **os.environ,
        "WAREHOUSE_ASSET_LINKS_JSON": json.dumps({"links": links}, ensure_ascii=False),
    }
    publisher = Path(__file__).with_name("publish-digital-assets.py")
    argv = [sys.executable or "python3", str(publisher)]
    if selected:
        argv.extend(["--repository", selected])
    if args.validate_config:
        argv.append("--validate-config")
    completed = subprocess.run(argv, env=child_env, check=False)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
