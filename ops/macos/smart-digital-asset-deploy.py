#!/usr/bin/env python3
"""Low-latency selective publisher for the Warehouse digital-asset Registry."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType
from typing import Any

DEFAULT_ROOT = Path("/Users/peiyuan/Server/bonfirework")
DEFAULT_CACHE_ROOT = DEFAULT_ROOT / "cache" / "digital-asset-smart-deploy"
DEFAULT_STATE_PATH = DEFAULT_CACHE_ROOT / "state.json"
DEFAULT_LOCK_PATH = DEFAULT_CACHE_ROOT / "watch.lock"
DEFAULT_INTERVAL_SECONDS = 3.0
DEFAULT_RETRY_SECONDS = 15.0
DEFAULT_FETCH_DEPTH = 2
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _load_module(filename: str, name: str) -> ModuleType:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _registry_module() -> ModuleType:
    return _load_module("publish-digital-assets-from-registry.py", "warehouse_registry_publisher")


def _publisher_module() -> ModuleType:
    return _load_module("publish-digital-assets.py", "warehouse_asset_publisher")


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=path.name + ".", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": "warehouse.digital-asset-smart-deploy.v1", "assets": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "warehouse.digital-asset-smart-deploy.v1", "assets": {}}
    if not isinstance(payload, dict):
        return {"schema": "warehouse.digital-asset-smart-deploy.v1", "assets": {}}
    if not isinstance(payload.get("assets"), dict):
        payload["assets"] = {}
    return payload


def _git_url(repository: str, *, use_ssh: bool) -> str:
    return f"git@github.com:{repository}.git" if use_ssh else f"https://github.com/{repository}.git"


def _remote_commit(
    registry: ModuleType,
    publisher: ModuleType,
    *,
    repository: str,
    ref: str,
    token: str,
    ssh_key: Path | None,
) -> str:
    use_ssh = not token.strip() and ssh_key is not None
    raw = publisher._run(
        ["git", "ls-remote", _git_url(repository, use_ssh=use_ssh), f"refs/heads/{ref}"],
        env=registry._git_environment(token, ssh_key if use_ssh else None),
        timeout=30,
    ).strip()
    fields = raw.split()
    if not fields or not COMMIT_RE.fullmatch(fields[0]):
        raise RuntimeError(f"unable to resolve {repository}@{ref}")
    return fields[0]


def _ensure_checkout(
    registry: ModuleType,
    publisher: ModuleType,
    *,
    checkout: Path,
    repository: str,
    ref: str,
    token: str,
    ssh_key: Path | None,
) -> str:
    checkout.parent.mkdir(parents=True, exist_ok=True)
    use_ssh = not token.strip() and ssh_key is not None
    env = registry._git_environment(token, ssh_key if use_ssh else None)
    url = _git_url(repository, use_ssh=use_ssh)
    if not (checkout / ".git").is_dir():
        publisher._run(
            [
                "git", "clone", "--depth", str(DEFAULT_FETCH_DEPTH), "--branch", ref,
                "--single-branch", "--no-tags", url, str(checkout),
            ],
            env=env,
            timeout=180,
        )
    else:
        publisher._run(["git", "remote", "set-url", "origin", url], cwd=checkout, timeout=30)
        publisher._run(
            [
                "git", "fetch", "--depth", str(DEFAULT_FETCH_DEPTH),
                "--no-tags", "origin", ref,
            ],
            cwd=checkout,
            env=env,
            timeout=120,
        )
        publisher._run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=checkout, timeout=30)
        publisher._run(["git", "clean", "-fdx"], cwd=checkout, timeout=30)
    commit = publisher._run(["git", "rev-parse", "HEAD"], cwd=checkout, timeout=30).strip()
    if not COMMIT_RE.fullmatch(commit):
        raise RuntimeError("Registry checkout returned an invalid commit")
    return commit


def _changed_files(
    publisher: ModuleType,
    *,
    checkout: Path,
    previous_commit: str,
    current_commit: str,
) -> set[str] | None:
    if not COMMIT_RE.fullmatch(previous_commit):
        return None
    try:
        raw = publisher._run(
            [
                "git", "diff", "--name-only", "--diff-filter=ACDMRTUXB",
                previous_commit, current_commit, "--",
            ],
            cwd=checkout,
            timeout=60,
        )
    except Exception:
        return None
    return {line.strip().strip("/") for line in raw.splitlines() if line.strip()}


def _affected_links(
    links: list[dict[str, Any]],
    *,
    registry_repository: str,
    registry_ref: str,
    registry_path: str,
    changed_files: set[str] | None,
    force_all: bool,
) -> list[dict[str, Any]]:
    registry_path = registry_path.strip().strip("/")
    candidates = [
        link
        for link in links
        if str(link.get("repository") or "") == registry_repository
        and str(link.get("ref") or "main") == registry_ref
    ]
    if force_all or changed_files is None or registry_path in changed_files:
        return candidates

    selected: list[dict[str, Any]] = []
    for link in candidates:
        source_path = str(link.get("source_path") or "").strip().strip("/")
        if not source_path:
            if changed_files:
                selected.append(link)
            continue
        prefix = source_path + "/"
        if any(path == source_path or path.startswith(prefix) for path in changed_files):
            selected.append(link)
    return selected


def _cached_cli(
    publisher: ModuleType,
    *,
    base_url: str,
    cache_root: Path,
    max_age_seconds: int = 300,
) -> Path:
    target = cache_root / "dam.py"
    cache_root.mkdir(parents=True, exist_ok=True)
    try:
        fresh = (
            target.is_file()
            and target.stat().st_size > 0
            and time.time() - target.stat().st_mtime < max_age_seconds
        )
    except OSError:
        fresh = False
    if not fresh:
        temporary = target.with_suffix(".tmp")
        publisher._download_cli(base_url, temporary)
        temporary.replace(target)
    return target


def _publish_links(
    publisher: ModuleType,
    *,
    links: list[dict[str, Any]],
    checkout: Path,
    registry_commit: str,
    base_url: str,
    cache_root: Path,
) -> list[dict[str, str]]:
    python = sys.executable or "python3"
    cli = _cached_cli(publisher, base_url=base_url, cache_root=cache_root)
    results: list[dict[str, str]] = []
    for link in links:
        repository = str(link["repository"])
        source_path = str(link.get("source_path") or "")
        version_no = (
            registry_commit
            if not source_path
            else f"{registry_commit}-{hashlib.sha256(source_path.encode('utf-8')).hexdigest()[:12]}"
        )
        workspace_env = publisher._workspace_environment(base_url, str(link["workspace_key"]))
        source_id = publisher._find_source_for_version(python, cli, workspace_env, version_no)
        source_reused = source_id is not None
        if source_id is None:
            source_id = publisher._push_source(
                python,
                cli,
                workspace_env,
                checkout,
                registry_commit,
                str(link.get("component") or ""),
                source_path,
                version_no,
            )
        release_id = publisher._create_release(
            python,
            cli,
            workspace_env,
            repository=repository,
            source_path=source_path,
            commit=registry_commit,
            source_id=source_id,
            runtime_type=str(link.get("runtime_type") or "auto"),
            component=str(link.get("component") or ""),
        )
        state = publisher._wait_for_release(
            python,
            cli,
            workspace_env,
            release_id,
            activate=bool(link.get("activate", True)),
            timeout_seconds=int(link.get("timeout_seconds") or 3600),
        )
        results.append(
            {
                "repository": repository,
                "source_path": source_path,
                "commit": registry_commit,
                "source_version": version_no,
                "source_version_id": source_id,
                "source": "reused" if source_reused else "uploaded",
                "release_id": release_id,
                "release_state": state,
            }
        )
    return results


def _scan_once(*, force_all: bool, cache_root: Path, state_path: Path) -> dict[str, Any]:
    registry = _registry_module()
    publisher = _publisher_module()
    repository = (
        os.environ.get("WAREHOUSE_ASSET_REGISTRY_REPOSITORY") or registry.DEFAULT_REGISTRY
    ).strip()
    ref = (os.environ.get("WAREHOUSE_ASSET_REGISTRY_REF") or registry.DEFAULT_REF).strip()
    registry_path_name = (
        os.environ.get("WAREHOUSE_ASSET_REGISTRY_PATH") or registry.DEFAULT_PATH
    ).strip()
    base_url = (os.environ.get("WAREHOUSE_BASE_URL") or "https://bonfirework.org").strip()
    token = os.environ.get("WAREHOUSE_ASSET_GITHUB_TOKEN") or ""
    ssh_key = registry._ssh_key()

    state = _load_state(state_path)
    previous_commit = str(state.get("registry_commit") or "")
    remote_commit = _remote_commit(
        registry,
        publisher,
        repository=repository,
        ref=ref,
        token=token,
        ssh_key=ssh_key,
    )
    checkout = cache_root / "registry"
    if (
        not force_all
        and previous_commit == remote_commit
        and (checkout / ".git").is_dir()
    ):
        return {"changed": False, "commit": remote_commit, "published": []}

    current_commit = _ensure_checkout(
        registry,
        publisher,
        checkout=checkout,
        repository=repository,
        ref=ref,
        token=token,
        ssh_key=ssh_key,
    )
    changed_files = _changed_files(
        publisher,
        checkout=checkout,
        previous_commit=previous_commit,
        current_commit=current_commit,
    )

    registry_file = (checkout / registry_path_name).resolve()
    try:
        registry_file.relative_to(checkout.resolve())
    except ValueError as exc:
        raise RuntimeError("Registry path escaped the persistent checkout") from exc
    if not registry_file.is_file():
        raise RuntimeError(f"Registry file not found: {registry_path_name}")

    workspace_keys = registry._workspace_keys()
    raw_links = registry._registry_links(registry_file, workspace_keys)
    links = publisher._load_links(json.dumps({"links": raw_links}, ensure_ascii=False))
    selected = _affected_links(
        links,
        registry_repository=repository,
        registry_ref=ref,
        registry_path=registry_path_name,
        changed_files=changed_files,
        force_all=force_all,
    )

    if not selected:
        state["registry_commit"] = current_commit
        state["updated_at"] = int(time.time())
        _atomic_json(state_path, state)
        return {
            "changed": previous_commit != current_commit,
            "commit": current_commit,
            "changed_files": sorted(changed_files or []),
            "published": [],
        }

    started = time.monotonic()
    results = _publish_links(
        publisher,
        links=selected,
        checkout=checkout,
        registry_commit=current_commit,
        base_url=base_url,
        cache_root=cache_root,
    )
    assets_state = state.setdefault("assets", {})
    for result in results:
        assets_state[f"{result['repository']}:{result['source_path']}"] = {
            "commit": current_commit,
            "release_id": result["release_id"],
            "release_state": result["release_state"],
            "updated_at": int(time.time()),
        }
    state["registry_commit"] = current_commit
    state["updated_at"] = int(time.time())
    _atomic_json(state_path, state)
    return {
        "changed": previous_commit != current_commit,
        "commit": current_commit,
        "changed_files": sorted(changed_files or []),
        "published": results,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch Registry main and selectively publish changed digital assets."
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--force-all", action="store_true")
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=float(
            os.environ.get("WAREHOUSE_ASSET_SMART_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)
        ),
    )
    parser.add_argument(
        "--cache-root",
        default=str(
            Path(
                os.environ.get("WAREHOUSE_ASSET_SMART_CACHE_ROOT") or DEFAULT_CACHE_ROOT
            ).expanduser()
        ),
    )
    parser.add_argument(
        "--state-path",
        default=str(
            Path(
                os.environ.get("WAREHOUSE_ASSET_SMART_STATE_PATH") or DEFAULT_STATE_PATH
            ).expanduser()
        ),
    )
    args = parser.parse_args()

    interval = max(1.0, min(float(args.interval_seconds), 60.0))
    cache_root = Path(args.cache_root).expanduser()
    state_path = Path(args.state_path).expanduser()
    lock_path = Path(
        os.environ.get("WAREHOUSE_ASSET_SMART_LOCK_PATH") or DEFAULT_LOCK_PATH
    ).expanduser()
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("digital-asset smart deploy is already running", flush=True)
            return

        if args.once:
            result = _scan_once(
                force_all=bool(args.force_all),
                cache_root=cache_root,
                state_path=state_path,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            return

        print(
            json.dumps(
                {
                    "watching": True,
                    "interval_seconds": interval,
                    "cache_root": str(cache_root),
                    "state_path": str(state_path),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        failure_delay = DEFAULT_RETRY_SECONDS
        while True:
            try:
                result = _scan_once(
                    force_all=False,
                    cache_root=cache_root,
                    state_path=state_path,
                )
                if result.get("changed") or result.get("published"):
                    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
                failure_delay = DEFAULT_RETRY_SECONDS
                time.sleep(interval)
            except KeyboardInterrupt:
                return
            except Exception as exc:
                print(
                    f"smart deploy scan failed: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(failure_delay)
                failure_delay = min(failure_delay * 2, 120.0)


if __name__ == "__main__":
    main()
