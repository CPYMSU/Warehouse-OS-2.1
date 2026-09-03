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
import shlex
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

COMMIT_RE = __import__("re").compile(r"^[0-9a-f]{40}$")


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
                "ConnectTimeout=12",
                "-o",
                "StrictHostKeyChecking=accept-new",
            ]
        ),
    }


def publish(args: argparse.Namespace) -> dict[str, str]:
    script_root = Path(__file__).resolve().parent
    publisher = load_module(script_root / "publish-digital-assets.py", "mk7_content_publisher")
    preparer = script_root / "prepare-resilient-digital-asset-cli.py"
    key = workspace_key(args.workspace_keys.expanduser(), args.workspace_alias)
    source_path = args.source_path.strip().strip("/")

    with tempfile.TemporaryDirectory(prefix="mk7-content-release-") as temporary:
        temp_root = Path(temporary)
        checkout = temp_root / "registry"
        run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                args.ref,
                "--single-branch",
                "--no-tags",
                f"git@github.com:{args.repository}.git",
                str(checkout),
            ],
            env=clone_environment(args.registry_ssh_key.expanduser()),
            timeout=600,
        )
        commit = run(["git", "rev-parse", "HEAD"], cwd=checkout, timeout=30).strip()
        if not COMMIT_RE.fullmatch(commit):
            raise RuntimeError("source checkout returned an invalid commit")

        version_no = (
            commit
            if not source_path
            else f"{commit}-{hashlib.sha256(source_path.encode('utf-8')).hexdigest()[:12]}"
        )
        cli = args.cache_root.expanduser() / "dam-content-only.py"
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
        source_id = publisher._find_source_for_version(
            python, cli, environment, version_no
        )
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
        result = {
            "repository": args.repository,
            "ref": args.ref,
            "source_path": source_path,
            "commit": commit,
            "source_version": version_no,
            "source_version_id": source_id,
            "source": source_origin,
            "release_id": release_id,
            "release_state": state,
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
