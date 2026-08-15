"""Versioned developer requirements shared by HTTP, CLI and the AI secretary."""

from __future__ import annotations

import json
from pathlib import Path

STANDARD_VERSION = "2.3"
STANDARD_SCHEMA = "warehouse.hosting-application.v2.3"
STANDARD_FILENAME = "workspace-hosting-developer-standard-2.3.zh-TW.md"
CONTRACT_FILENAME = "workspace-hosting-contract-2.3.json"


def _document_path(filename: str) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    packaged_root = Path(__file__).resolve().parents[2]
    for candidate in (
        source_root / "docs" / filename,
        packaged_root / "docs" / filename,
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(filename)


def standard_path() -> Path:
    return _document_path(STANDARD_FILENAME)


def contract_path() -> Path:
    return _document_path(CONTRACT_FILENAME)


def requirement_downloads(*, public_surface: str) -> list[dict[str, str]]:
    if public_surface == "hosting":
        standard_url = "/api/hosting/v2/developer-standard.md"
        contract_url = "/api/hosting/v2/contract.json"
    else:
        standard_url = "/api/digital-assets/hosting-standard/download"
        contract_url = "/api/digital-assets/hosting-contract.json"
    return [
        {
            "label": "下載《託管應用技術要求 2.3》",
            "name": STANDARD_FILENAME,
            "url": standard_url,
            "filename": STANDARD_FILENAME,
            "media_type": "text/markdown",
        },
        {
            "label": "下載機器可讀 Hosting Contract 2.3",
            "name": CONTRACT_FILENAME,
            "url": contract_url,
            "filename": CONTRACT_FILENAME,
            "media_type": "application/json",
        },
    ]


def requirements_bundle(*, public_surface: str) -> dict[str, object]:
    contract = json.loads(contract_path().read_text(encoding="utf-8"))
    return {
        "ok": True,
        "version": STANDARD_VERSION,
        "schema": STANDARD_SCHEMA,
        "release_orchestration": {
            "schema": "warehouse.workspace-release.v1",
            "cli_version": "2.8.0",
            "doctor": "python3 dm.py project doctor --source <SOURCE_VERSION_ID>",
            "run": (
                "python3 dm.py release run --source <SOURCE_VERSION_ID> "
                "--idempotency-key <STABLE_KEY>"
            ),
            "implicit_activation": False,
            "server_owned_progress": True,
        },
        "content": standard_path().read_text(encoding="utf-8"),
        "contract": contract,
        "downloads": requirement_downloads(public_surface=public_surface),
        "note": (
            "文件與機器契約使用同一版本；AI 應依 contract 回答並把 downloads "
            "原樣交給需要下載的使用者。"
        ),
    }
