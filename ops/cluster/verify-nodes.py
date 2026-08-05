#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def fetch(url: str, timeout: float) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "warehouse-cluster-verify/1"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        value = json.load(response)
    if not isinstance(value, dict):
        raise RuntimeError(f"{url} did not return a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify all declared production nodes")
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path(__file__).with_name("nodes.json"),
    )
    parser.add_argument("--release", default=os.getenv("WAREHOUSE_EXPECTED_RELEASE", ""))
    parser.add_argument("--git-sha", default=os.getenv("WAREHOUSE_EXPECTED_GIT_SHA", ""))
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--allow-version-skew", action="store_true")
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    observations: list[dict[str, object]] = []
    failures: list[str] = []
    for declared in inventory["nodes"]:
        node_id = str(declared["id"])
        override = os.getenv(f"WAREHOUSE_NODE_URL_{node_id.upper().replace('-', '_')}")
        url = override or str(declared["health_url"])
        try:
            observed = fetch(url, args.timeout)
        except (OSError, RuntimeError, urllib.error.URLError) as exc:
            failures.append(f"{node_id}: unreachable ({type(exc).__name__})")
            continue
        observations.append(observed)
        if observed.get("schema") != "warehouse.cluster-node.v1":
            failures.append(f"{node_id}: incompatible identity schema")
        if observed.get("node_id") != node_id:
            failures.append(f"{node_id}: reported node_id={observed.get('node_id')!r}")
        if observed.get("node_role") != declared["role"]:
            failures.append(f"{node_id}: reported role={observed.get('node_role')!r}")
        if observed.get("platform") != declared["platform"]:
            failures.append(f"{node_id}: reported platform={observed.get('platform')!r}")
        if observed.get("status") != "ready" or observed.get("database") != "ready":
            failures.append(f"{node_id}: application or database is not ready")
        if args.release and observed.get("release_id") != args.release:
            failures.append(f"{node_id}: release does not match {args.release}")
        if args.git_sha and not str(observed.get("git_sha", "")).startswith(args.git_sha):
            failures.append(f"{node_id}: git SHA does not match {args.git_sha}")
        if declared["expected_peer"] not in (observed.get("peers") or []):
            failures.append(f"{node_id}: peer inventory is incomplete")

    releases = {str(item.get("release_id")) for item in observations}
    schemas = {str(item.get("alembic_head")) for item in observations}
    if not args.allow_version_skew and len(releases) > 1:
        failures.append(f"release skew detected: {sorted(releases)}")
    if len(schemas) > 1:
        failures.append(f"database schema skew detected: {sorted(schemas)}")

    print(
        json.dumps(
            {"ok": not failures, "nodes": observations, "failures": failures},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
