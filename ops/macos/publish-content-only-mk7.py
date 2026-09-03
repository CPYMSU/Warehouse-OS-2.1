#!/usr/bin/env python3
"""Publish one immutable MK7 content-only branch through Warehouse releases.

This is a narrow release adapter for a source revision that changes site/course
content only. The source branch owns a hosting manifest with no required
lifecycle database jobs, while keeping candidate build, database-health
acceptance, explicit activation, exact public-route verification and rollback.
No workspace key or repository credential is written to Git or stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import ModuleType
from typing import Any

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
COURSE_MARKERS = ("更换间隔棒", "习惯性违章")


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 900,
) -> str:
    completed = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "command failed").strip()
        raise RuntimeError(f"{argv[0]} failed: {message[-1800:]}")
    return completed.stdout


def private_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"required private file is missing: {path}")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise RuntimeError(f"private file must have mode 0600: {path}")


def workspace_key(path: Path, alias: str) -> str:
    private_file(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("workspace key file must be a JSON object")
    key = str(value.get(alias) or "").strip()
    if not key.startswith("wak_"):
        raise RuntimeError(f"workspace key alias is unavailable: {alias}")
    return key


def clone_environment(ssh_key: Path) -> dict[str, str]:
    private_file(ssh_key)
    return {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_SSH_COMMAND": " ".join(
            [
                "/usr/bin/ssh",
                "-i",
                shlex.quote(str(ssh_key)),
                "-o",
                "Hostname=ssh.github.com",
                "-p",
                "443",
                "-o",
                "BatchMode=yes",
                "-o",
                "IdentitiesOnly=yes",
                "-o",
                "ConnectTimeout=15",
                "-o",
                "ServerAliveInterval=15",
                "-o",
                "ServerAliveCountMax=8",
                "-o",
                "TCPKeepAlive=yes",
                "-o",
                "IPQoS=throughput",
                "-o",
                "StrictHostKeyChecking=accept-new",
            ]
        ),
    }


def _remove_git_locks(checkout: Path) -> None:
    git_dir = checkout / ".git"
    if not git_dir.is_dir():
        return
    for lock in git_dir.rglob("*.lock"):
        try:
            lock.unlink()
        except OSError:
            pass


def _prepare_repository(checkout: Path, repository: str) -> None:
    url = f"git@github.com:{repository}.git"
    if not (checkout / ".git").is_dir():
        if checkout.exists():
            shutil.rmtree(checkout)
        checkout.mkdir(parents=True, exist_ok=True)
        run(["git", "init"], cwd=checkout, timeout=30)
        run(["git", "remote", "add", "origin", url], cwd=checkout, timeout=30)
    else:
        _remove_git_locks(checkout)
        run(["git", "remote", "set-url", "origin", url], cwd=checkout, timeout=30)
    run(["git", "config", "core.compression", "0"], cwd=checkout, timeout=30)
    run(["git", "config", "fetch.prune", "true"], cwd=checkout, timeout=30)


def checkout_source(
    *,
    cache_root: Path,
    repository: str,
    ref: str,
    ssh_key: Path,
) -> tuple[Path, str]:
    """Fetch only the immutable candidate delta into the persistent Registry cache."""

    cache_root.mkdir(parents=True, exist_ok=True)
    normal_cache = cache_root / "registry"
    checkout = normal_cache if (normal_cache / ".git").is_dir() else cache_root / "registry-content-only"
    _prepare_repository(checkout, repository)
    environment = clone_environment(ssh_key)
    remote_ref = "refs/remotes/origin/mk7-content-only-release"
    source_ref = f"refs/heads/{ref}"
    failures: list[str] = []

    for attempt in range(1, 13):
        _remove_git_locks(checkout)
        completed = subprocess.run(
            [
                "git",
                "-c",
                "core.compression=0",
                "fetch",
                "--depth",
                "2",
                "--force",
                "--no-tags",
                "--no-recurse-submodules",
                "origin",
                f"+{source_ref}:{remote_ref}",
            ],
            cwd=str(checkout),
            env=environment,
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
        )
        if completed.returncode == 0:
            run(["git", "reset", "--hard", remote_ref], cwd=checkout, timeout=60)
            run(["git", "clean", "-fdx"], cwd=checkout, timeout=60)
            commit = run(["git", "rev-parse", "HEAD"], cwd=checkout, timeout=30).strip()
            if not COMMIT_RE.fullmatch(commit):
                raise RuntimeError("source checkout returned an invalid commit")
            print(
                json.dumps(
                    {
                        "source_checkout": "ready",
                        "repository": repository,
                        "ref": ref,
                        "commit": commit,
                        "fetch_attempt": attempt,
                        "cache": str(checkout),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                flush=True,
            )
            return checkout, commit

        error = (completed.stderr or completed.stdout or "git fetch failed").strip()
        failures.append(error[-500:])
        print(
            json.dumps(
                {
                    "source_checkout": "retrying",
                    "attempt": attempt,
                    "reason": error[-300:],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        time.sleep(min(10 * attempt, 60))

    raise RuntimeError(
        "unable to fetch the immutable MK7 content branch after retries: "
        + " | ".join(failures[-3:])
    )


def _read_url(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Cache-Control": "no-cache",
            "User-Agent": "Warehouse-MK7-PostActivation-Verification/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return int(response.status), response.read(2 * 1024 * 1024)


def verify_public_course() -> dict[str, Any]:
    """Verify the activated course through the public custom host or stable entry."""

    candidates = [
        "https://mk7-workspace.bonfirework.org/learn/500kv-spacer-habitual-violations/",
        "https://bonfirework.org/assets/bonfire/mk7-workspace/learn/500kv-spacer-habitual-violations/",
    ]
    observations: list[dict[str, object]] = []
    for round_no in range(1, 13):
        for url in candidates:
            try:
                status, raw = _read_url(url)
                text = raw.decode("utf-8", "replace")
                markers = {marker: marker in text for marker in COURSE_MARKERS}
                observation = {
                    "url": url,
                    "status": status,
                    "markers": markers,
                    "bytes": len(raw),
                    "round": round_no,
                }
                observations.append(observation)
                if status == 200 and all(markers.values()):
                    print(
                        json.dumps(
                            {"public_course_verification": "passed", **observation},
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        flush=True,
                    )
                    return observation
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
                observations.append(
                    {
                        "url": url,
                        "status": getattr(exc, "code", None),
                        "error": type(exc).__name__,
                        "round": round_no,
                    }
                )
        time.sleep(min(round_no * 5, 30))
    raise RuntimeError(
        "activated release did not become observable at the MK7 public course route: "
        + json.dumps(observations[-6:], ensure_ascii=False, default=str)
    )


def publish(args: argparse.Namespace) -> dict[str, Any]:
    script_root = Path(__file__).resolve().parent
    publisher = load_module(script_root / "publish-digital-assets.py", "mk7_content_publisher")
    preparer = script_root / "prepare-resilient-digital-asset-cli.py"
    key = workspace_key(args.workspace_keys.expanduser(), args.workspace_alias)
    source_path = args.source_path.strip().strip("/")
    cache_root = args.cache_root.expanduser()

    checkout, commit = checkout_source(
        cache_root=cache_root,
        repository=args.repository,
        ref=args.ref,
        ssh_key=args.registry_ssh_key.expanduser(),
    )

    version_no = (
        commit
        if not source_path
        else f"{commit}-{hashlib.sha256(source_path.encode('utf-8')).hexdigest()[:12]}"
    )
    cli = cache_root / "dam-content-only.py"
    run(
        [
            sys.executable or "python3",
            str(preparer),
            str(cli),
            "--base-url",
            args.base_url,
        ],
        timeout=600,
    )
    python = sys.executable or "python3"
    environment = publisher._workspace_environment(args.base_url, key)
    source_id = publisher._find_source_for_version(python, cli, environment, version_no)
    source_origin = "reused"
    if source_id is None:
        source_id = publisher._push_source(
            python,
            cli,
            environment,
            checkout,
            commit,
            "",
            source_path,
            version_no,
        )
        source_origin = "uploaded"

    release_id = publisher._create_release(
        python,
        cli,
        environment,
        repository=args.repository,
        source_path=source_path,
        commit=commit,
        source_id=source_id,
        runtime_type="auto",
        component="",
    )
    state = publisher._wait_for_release(
        python,
        cli,
        environment,
        release_id,
        activate=True,
        timeout_seconds=args.timeout_seconds,
    )
    if state != "verified":
        raise RuntimeError(f"release did not finish verified: {state}")
    public_verification = verify_public_course()
    result: dict[str, Any] = {
        "repository": args.repository,
        "ref": args.ref,
        "source_path": source_path,
        "commit": commit,
        "source_version": version_no,
        "source_version_id": source_id,
        "source": source_origin,
        "release_id": release_id,
        "release_state": state,
        "public_course": public_verification,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="CPYMSU/registry")
    parser.add_argument("--ref", default="chatgpt/mk7-content-v231")
    parser.add_argument("--source-path", default="assets/mk7")
    parser.add_argument("--workspace-alias", default="mk7")
    parser.add_argument(
        "--workspace-keys",
        type=Path,
        default=Path(
            "/Users/peiyuan/Server/bonfirework/secrets/digital-asset-workspace-keys.json"
        ),
    )
    parser.add_argument(
        "--registry-ssh-key",
        type=Path,
        default=Path(
            "/Users/peiyuan/Server/bonfirework/secrets/registry-readonly-ed25519-v2"
        ),
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path("/Users/peiyuan/Server/bonfirework/cache/digital-asset-smart-deploy"),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("WAREHOUSE_BASE_URL") or "https://bonfirework.org",
    )
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    args = parser.parse_args()
    publish(args)


if __name__ == "__main__":
    main()
