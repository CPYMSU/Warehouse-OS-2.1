#!/usr/bin/env python3
"""Select an admin-capable key for one configured workspace without disclosure.

The source JSON contains local aliases mapped to ``wak_`` values. This helper
probes `/api/workspaces/v1/info`, compares every candidate with the target
workspace, and writes a temporary 0600 JSON file containing only the selected
key. It prints aliases and scope names only; token values are never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REQUIRED = frozenset({"deploy:read", "deploy:write", "database:admin"})


def load_keys(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError(f"workspace key file is missing: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        raise RuntimeError(f"workspace key file must be mode 0600: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("workspace key file must contain a JSON object")
    keys: dict[str, str] = {}
    for raw_alias, raw_key in value.items():
        alias = str(raw_alias).strip()
        key = str(raw_key).strip()
        if alias and key.startswith("wak_"):
            keys[alias] = key
    return keys


def info(base_url: str, key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/workspaces/v1/info",
        headers={
            "Authorization": "Bearer " + key,
            "Accept": "application/json",
            "User-Agent": "Warehouse-Admin-Key-Selector/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"workspace info returned HTTP {exc.code}: {raw[-500:]}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("workspace info returned a non-object response")
    return value


def workspace_identity(value: dict[str, Any]) -> str:
    workspace = value.get("workspace") if isinstance(value.get("workspace"), dict) else {}
    return str(
        value.get("workspace_id")
        or workspace.get("uuid")
        or workspace.get("id")
        or value.get("workspace_key")
        or workspace.get("key")
        or ""
    )


def scopes(value: dict[str, Any]) -> frozenset[str]:
    credential = value.get("credential") if isinstance(value.get("credential"), dict) else {}
    raw = value.get("scopes") or credential.get("scopes") or []
    return frozenset(str(item) for item in raw if str(item))


def select(
    source: Path,
    target_alias: str,
    output: Path,
    base_url: str,
) -> dict[str, object]:
    keys = load_keys(source)
    target_key = keys.get(target_alias)
    if target_key is None:
        raise RuntimeError(f"target workspace alias is missing: {target_alias}")
    target_info = info(base_url, target_key)
    target_identity = workspace_identity(target_info)
    if not target_identity:
        raise RuntimeError("target workspace identity is unavailable")

    inspected: list[dict[str, object]] = []
    selected_alias = ""
    selected_key = ""
    for alias, key in keys.items():
        try:
            observed = info(base_url, key)
        except Exception as exc:
            inspected.append({"alias": alias, "usable": False, "reason": type(exc).__name__})
            continue
        observed_identity = workspace_identity(observed)
        observed_scopes = scopes(observed)
        same_workspace = observed_identity == target_identity
        has_required = REQUIRED.issubset(observed_scopes)
        inspected.append(
            {
                "alias": alias,
                "usable": same_workspace and has_required,
                "same_workspace": same_workspace,
                "scopes": sorted(observed_scopes),
            }
        )
        if same_workspace and has_required and not selected_key:
            selected_alias = alias
            selected_key = key

    if not selected_key:
        safe = json.dumps(inspected, ensure_ascii=False, sort_keys=True)
        raise RuntimeError(
            "no key for the target workspace has deploy:read, deploy:write and "
            f"database:admin; inspected={safe}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps({target_alias: selected_key}), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(output)
    os.chmod(output, 0o600)
    print(
        json.dumps(
            {
                "ok": True,
                "target_alias": target_alias,
                "selected_alias": selected_alias,
                "required_scopes": sorted(REQUIRED),
                "output": str(output),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return {"selected_alias": selected_alias, "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target-alias", default="mk7")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("WAREHOUSE_BASE_URL") or "https://bonfirework.org",
    )
    args = parser.parse_args()
    select(
        args.source.expanduser(),
        str(args.target_alias),
        args.output.expanduser(),
        str(args.base_url),
    )


if __name__ == "__main__":
    main()
