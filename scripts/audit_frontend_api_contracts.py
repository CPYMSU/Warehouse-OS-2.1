#!/usr/bin/env python3
"""Audit retained frontend API calls against the FastAPI OpenAPI contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CLIENT_ROOTS = (
    ROOT / "frontend" / "v2",
    ROOT / "frontend",
    ROOT / "mobile" / "src",
    ROOT / "wechat-miniapp" / "miniprogram",
)
EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".html"}
SKIP_PARTS = {"vendor", "dist", "node_modules", "miniprogram_npm"}

CALL_PATTERNS = (
    (re.compile(r"\bW2\.json\s*\(\s*(?P<expr>[^,\n]+)"), "GET"),
    (re.compile(r"\bW2\.post\s*\(\s*(?P<expr>[^,\n]+)"), "POST"),
    (re.compile(r"\bpublicPost\s*\(\s*(?P<expr>[^,\n]+)"), "POST"),
    (re.compile(r"\bverificationPost\s*\(\s*(?P<expr>[^,\n]+)"), "POST"),
    (
        re.compile(
            r"\b(?:api|client|http|request)\.(?P<method>get|post|put|patch|delete)"
            r"\s*\(\s*(?P<expr>[^,\n]+)",
            re.I,
        ),
        None,
    ),
    (re.compile(r"\bfetch\s*\(\s*(?P<expr>[^,\n]+)"), "FETCH"),
)

QUOTED_PART = re.compile(r"^\s*([\"'`])(?P<body>.*)\1\s*$", re.S)
TEMPLATE_EXPR = re.compile(r"\$\{[^}]+\}")
PATH_PARAM = re.compile(r"\{[^}/]+\}")


@dataclass(frozen=True, order=True)
class Contract:
    method: str
    path: str
    source: str
    line: int


def iter_sources() -> Iterable[Path]:
    seen: set[Path] = set()
    for root in CLIENT_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def simple_js_expression(expr: str) -> str | None:
    """Resolve a simple JS string/template/concatenation into an API template."""
    expr = expr.strip()
    if not expr:
        return None
    pieces = re.split(r"\s*\+\s*", expr)
    output: list[str] = []
    for piece in pieces:
        piece = piece.strip().strip("()")
        match = QUOTED_PART.match(piece)
        if match:
            output.append(TEMPLATE_EXPR.sub("{param}", match.group("body")))
            continue
        if re.fullmatch(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*", piece):
            output.append("{param}")
            continue
        return None
    value = "".join(output)
    api_at = value.find("/api/")
    if api_at < 0:
        return None
    value = value[api_at:]
    value = value.split("#", 1)[0].split("?", 1)[0]
    value = re.sub(r"/+", "/", value)
    value = re.sub(r"\{param\}(?=\{param\})", "{param}", value)
    # A variable appended directly to the end of a complete path is the common
    # `?query`/cursor suffix pattern. Dynamic path IDs are preceded by `/` and
    # therefore remain as `{param}`.
    value = re.sub(r"(?<=[A-Za-z0-9_-])\{param\}$", "", value)
    return value.rstrip("/") or "/api"


def fetch_method(snippet: str) -> str:
    match = re.search(
        r"\bmethod\s*:\s*[\"'](GET|POST|PUT|PATCH|DELETE)[\"']",
        snippet,
        re.I,
    )
    return match.group(1).upper() if match else "GET"


def scan_file(path: Path) -> list[Contract]:
    try:
        text_value = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    relative = path.relative_to(ROOT).as_posix()
    contracts: set[Contract] = set()
    lines = text_value.splitlines()
    for number, line in enumerate(lines, start=1):
        if "/api" not in line:
            continue
        window = "\n".join(lines[number - 1 : min(len(lines), number + 7)])
        for pattern, fixed_method in CALL_PATTERNS:
            for match in pattern.finditer(line):
                path_value = simple_js_expression(match.group("expr"))
                if not path_value:
                    continue
                if fixed_method == "FETCH":
                    method = fetch_method(window)
                elif fixed_method:
                    method = fixed_method
                    if fixed_method == "GET":
                        explicit = fetch_method(window)
                        if explicit != "GET":
                            method = explicit
                else:
                    method = match.group("method").upper()
                contracts.add(Contract(method, path_value, relative, number))
    return sorted(contracts)


def path_shape(path: str) -> tuple[str, ...]:
    return tuple(
        "{}" if PATH_PARAM.fullmatch(segment) else segment
        for segment in path.strip("/").split("/")
    )


def paths_compatible(frontend_path: str, backend_path: str) -> bool:
    left = path_shape(frontend_path)
    right = path_shape(backend_path)
    if len(left) != len(right):
        return False
    return all(a == b or a == "{}" or b == "{}" for a, b in zip(left, right, strict=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-missing", action="store_true")
    parser.add_argument("--report", default="frontend-api-contract-report.json")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import app

    openapi_paths: dict[str, dict[str, object]] = app.openapi().get("paths", {})
    discovered: list[Contract] = []
    source_paths = list(iter_sources())
    for path in source_paths:
        discovered.extend(scan_file(path))

    unique: dict[tuple[str, str], list[Contract]] = {}
    for contract in discovered:
        unique.setdefault((contract.method, contract.path), []).append(contract)

    missing: list[dict[str, object]] = []
    connected: list[dict[str, object]] = []
    for (method, frontend_path), sources in sorted(unique.items()):
        matches = [
            backend_path
            for backend_path, operations in openapi_paths.items()
            if method.lower() in operations and paths_compatible(frontend_path, backend_path)
        ]
        row = {
            "method": method,
            "path": frontend_path,
            "sources": [f"{item.source}:{item.line}" for item in sources],
            "backend_matches": matches,
        }
        (connected if matches else missing).append(row)

    report = {
        "scanned_files": len(source_paths),
        "discovered_contracts": len(unique),
        "connected_contracts": len(connected),
        "missing_contracts": len(missing),
        "missing": missing,
        "connected": connected,
    }
    report_path = ROOT / args.report
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "scanned_files",
                    "discovered_contracts",
                    "connected_contracts",
                    "missing_contracts",
                )
            },
            ensure_ascii=False,
        )
    )
    for row in missing:
        print(f"MISSING {row['method']} {row['path']} <- {', '.join(row['sources'])}")
    return 1 if args.fail_on_missing and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
