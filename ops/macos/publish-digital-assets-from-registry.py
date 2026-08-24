#!/usr/bin/env python3
"""Publish governed digital assets from the dedicated Git registry.

The registry stores no Warehouse credentials. Workspace keys may come from the
legacy Actions JSON secret, but the production Mac mini defaults to a local
0600 JSON file. A private Registry repository may likewise be read with an
Actions token or a runner-local read-only SSH deploy key.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath
from types import ModuleType
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
    "/Users/peiyuan/Server/bonfirework/secrets/registry-readonly-ed25519"
)


def _publisher() -> ModuleType:
    path = Path(__file__).with_name("publish-digital-assets.py")
    spec = importlib.util.spec_from_file_location("warehouse_asset_publisher", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load the digital-asset publisher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json_object(raw: str, *, source: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{source} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{source} must be a JSON object")
    return value


def _require_private_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"required local credential file is missing: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        raise RuntimeError(f"local credential file must have mode 0600: {path}")
    parent_mode = stat.S_IMODE(path.parent.stat().st_mode)
    if parent_mode & 0o077:
        raise RuntimeError(f"local credential directory must not be group/world accessible: {path.parent}")


def _workspace_keys() -> dict[str, str]:
    raw = (os.environ.get("WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON") or "").strip()
    if raw:
        values = _load_json_object(raw, source="WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON")
    else:
        path = Path(
            os.environ.get("WAREHOUSE_ASSET_WORKSPACE_KEYS_FILE")
            or DEFAULT_WORKSPACE_KEYS_FILE
        ).expanduser()
        _require_private_file(path)
        values = _load_json_object(path.read_text(encoding="utf-8"), source=str(path))

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


def _ssh_key() -> Path | None:
    raw = (
        os.environ.get("WAREHOUSE_ASSET_REGISTRY_SSH_KEY")
        or os.environ.get("WAREHOUSE_ASSET_GITHUB_SSH_KEY")
        or ""
    ).strip()
    path = Path(raw).expanduser() if raw else DEFAULT_REGISTRY_SSH_KEY
    if not path.exists():
        return None
    _require_private_file(path)
    return path


def _git_environment(token: str, ssh_key: Path | None) -> dict[str, str]:
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
    elif ssh_key is not None:
        env["GIT_SSH_COMMAND"] = " ".join(
            [
                "ssh",
                "-i",
                shlex.quote(str(ssh_key)),
                "-o",
                "BatchMode=yes",
                "-o",
                "IdentitiesOnly=yes",
                "-o",
                "StrictHostKeyChecking=accept-new",
            ]
        )
    return env


def _clone_repository(
    publisher: ModuleType,
    *,
    repository: str,
    ref: str,
    target: Path,
    registry_repository: str,
    token: str,
    ssh_key: Path | None,
) -> None:
    if not REPOSITORY_RE.fullmatch(repository):
        raise RuntimeError(f"invalid source repository: {repository!r}")
    use_ssh = not token.strip() and ssh_key is not None and repository == registry_repository
    url = (
        f"git@github.com:{repository}.git"
        if use_ssh
        else f"https://github.com/{repository}.git"
    )
    publisher._run(
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
            str(target),
        ],
        env=_git_environment(token, ssh_key if use_ssh else None),
        timeout=600,
    )


def _registry_links(path: Path, workspace_keys: dict[str, str]) -> list[dict[str, Any]]:
    payload = _load_json_object(path.read_text(encoding="utf-8"), source=str(path))
    schema = str(payload.get("schema") or "").strip()
    if schema and schema != "warehouse.digital-asset-registry.v1":
        raise RuntimeError(f"unsupported registry schema: {schema!r}")
    links = payload.get("links")
    if not isinstance(links, list):
        raise RuntimeError("registry.json must contain a links array")

    resolved: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
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
        if source_path:
            parsed = PurePosixPath(source_path)
            if parsed.is_absolute() or ".." in parsed.parts:
                raise RuntimeError(f"registry link {repository} has unsafe source_path")
        identity = (repository, source_path)
        if identity in seen:
            raise RuntimeError(
                f"registry contains duplicate asset binding {repository}:{source_path}"
            )
        seen.add(identity)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish the dedicated Registry through Mac-local least-privilege credentials."
    )
    parser.add_argument("--repository", help="Publish only one owner/repository binding.")
    parser.add_argument("--validate-config", action="store_true")
    args = parser.parse_args()

    publisher = _publisher()
    registry_repository = (
        os.environ.get("WAREHOUSE_ASSET_REGISTRY_REPOSITORY") or DEFAULT_REGISTRY
    ).strip()
    registry_ref = (os.environ.get("WAREHOUSE_ASSET_REGISTRY_REF") or DEFAULT_REF).strip()
    relative_path = (os.environ.get("WAREHOUSE_ASSET_REGISTRY_PATH") or DEFAULT_PATH).strip()
    if not REPOSITORY_RE.fullmatch(registry_repository):
        raise RuntimeError(f"invalid registry repository: {registry_repository!r}")
    if not registry_ref:
        raise RuntimeError("WAREHOUSE_ASSET_REGISTRY_REF cannot be empty")
    if not relative_path or relative_path.startswith("/") or ".." in Path(relative_path).parts:
        raise RuntimeError("WAREHOUSE_ASSET_REGISTRY_PATH must be a safe relative path")

    github_token = os.environ.get("WAREHOUSE_ASSET_GITHUB_TOKEN") or ""
    ssh_key = _ssh_key()
    workspace_keys = _workspace_keys()
    selected = (args.repository or os.environ.get("WAREHOUSE_ASSET_REPOSITORY") or "").strip()
    base_url = (os.environ.get("WAREHOUSE_BASE_URL") or "https://bonfirework.org").strip()

    failures: list[dict[str, str]] = []
    results: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="warehouse-asset-registry-") as temporary:
        temp_root = Path(temporary)
        registry_checkout = temp_root / "registry"
        _clone_repository(
            publisher,
            repository=registry_repository,
            ref=registry_ref,
            target=registry_checkout,
            registry_repository=registry_repository,
            token=github_token,
            ssh_key=ssh_key,
        )
        registry_path = (registry_checkout / relative_path).resolve()
        try:
            registry_path.relative_to(registry_checkout.resolve())
        except ValueError as exc:
            raise RuntimeError("registry path escaped the checkout") from exc
        if not registry_path.is_file():
            raise RuntimeError(f"registry file not found: {relative_path}")

        raw_links = _registry_links(registry_path, workspace_keys)
        links = publisher._load_links(
            json.dumps({"links": raw_links}, ensure_ascii=False)
        )
        if selected:
            links = [link for link in links if str(link.get("repository")) == selected]
            if not links:
                raise SystemExit(
                    f"repository {selected!r} is not configured in the digital-asset registry"
                )
        if args.validate_config:
            print(json.dumps({"ok": True, "links": len(links)}, ensure_ascii=False))
            return
        if not links:
            print("No enabled digital assets are configured; nothing to publish.")
            return

        cli = temp_root / "dam.py"
        publisher._download_cli(base_url, cli)
        python = sys.executable or "python3"
        registry_commit = publisher._run(
            ["git", "rev-parse", "HEAD"], cwd=registry_checkout, timeout=30
        ).strip()

        for number, link in enumerate(links, start=1):
            repository = str(link["repository"])
            ref = str(link["ref"])
            source_path = str(link.get("source_path") or "")
            try:
                if repository == registry_repository and ref == registry_ref:
                    checkout = registry_checkout
                    commit = registry_commit
                else:
                    checkout = temp_root / f"source-{number}"
                    _clone_repository(
                        publisher,
                        repository=repository,
                        ref=ref,
                        target=checkout,
                        registry_repository=registry_repository,
                        token=github_token,
                        ssh_key=ssh_key,
                    )
                    commit = publisher._run(
                        ["git", "rev-parse", "HEAD"], cwd=checkout, timeout=30
                    ).strip()
                if not re.fullmatch(r"[0-9a-f]{40}", commit):
                    raise RuntimeError(f"{repository} returned an invalid commit id")

                version_no = (
                    commit
                    if not source_path
                    else f"{commit}-{hashlib.sha256(source_path.encode('utf-8')).hexdigest()[:12]}"
                )
                workspace_env = publisher._workspace_environment(
                    base_url, str(link["workspace_key"])
                )
                source_id = publisher._find_source_for_version(
                    python, cli, workspace_env, version_no
                )
                source_reused = source_id is not None
                if source_id is None:
                    source_id = publisher._push_source(
                        python,
                        cli,
                        workspace_env,
                        checkout,
                        commit,
                        str(link["component"]),
                        source_path,
                        version_no,
                    )
                release_id = publisher._create_release(
                    python,
                    cli,
                    workspace_env,
                    repository=repository,
                    source_path=source_path,
                    commit=commit,
                    source_id=source_id,
                    runtime_type=str(link["runtime_type"]),
                    component=str(link["component"]),
                )
                state = publisher._wait_for_release(
                    python,
                    cli,
                    workspace_env,
                    release_id,
                    activate=bool(link["activate"]),
                    timeout_seconds=int(link["timeout_seconds"]),
                )
                results.append(
                    {
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
                )
            except Exception as exc:
                failures.append(
                    {
                        "repository": repository,
                        "source_path": source_path,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                print(
                    f"publish failed for {repository}:{source_path}: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

    print(json.dumps({"published": results, "failures": failures}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
