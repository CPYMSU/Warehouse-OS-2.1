#!/usr/bin/env python3
"""Resolve a Git-backed digital-asset registry, then invoke the Mac publisher.

The registry contains no Warehouse credentials. Each entry names a
``workspace_key_ref``; the corresponding ``wak_`` value comes only from the
``WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON`` Actions secret.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
KEY_REF_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
DEFAULT_REGISTRY = "CPYMSU/Warehouse-Digital-Asset-Registry"
DEFAULT_REF = "main"
DEFAULT_PATH = "registry.json"


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


def _load_json_object(raw: str, *, source: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{source} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{source} must be a JSON object")
    return value


def _workspace_keys() -> dict[str, str]:
    raw = os.environ.get("WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON") or ""
    values = _load_json_object(raw, source="WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON")
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
    links = payload.get("links")
    if not isinstance(links, list):
        raise RuntimeError("registry.json must contain a links array")

    resolved: list[dict[str, Any]] = []
    seen_repositories: set[str] = set()
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
        if repository in seen_repositories:
            raise RuntimeError(f"registry contains duplicate repository {repository!r}")
        seen_repositories.add(repository)
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
            f"https://github.com/{repository}.git",
            str(checkout),
        ],
        env=_git_environment(token),
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
