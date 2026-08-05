"""Versioned developer requirements shared by HTTP, CLI and the AI secretary."""

from __future__ import annotations

import json
from pathlib import Path

STANDARD_VERSION = "2.3"
STANDARD_SCHEMA = "warehouse.hosting-application.v2.3"
STANDARD_FILENAME = "workspace-hosting-developer-standard-2.3.zh-TW.md"
CONTRACT_FILENAME = "workspace-hosting-contract-2.3.json"
AUTO_RUNTIME_GUIDE_FILENAME = "warehouse-hosting-mechanisms-2.3.zh-TW.md"


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


def auto_runtime_guide_path() -> Path:
    """Return the single guide shared by the secretary and terminal AIs."""

    return _document_path(AUTO_RUNTIME_GUIDE_FILENAME)


def auto_runtime_guide_bundle(*, public_surface: str = "hosting") -> dict[str, object]:
    """Return the guide as a complete secretary-safe JSON envelope.

    The Markdown route remains the canonical file download.  This envelope is
    also needed by the shared command executor: a ``FileResponse`` is treated
    as a bounded text response by the internal HTTP adapter and therefore
    cannot reliably deliver the complete guide to an AI secretary.
    """

    if public_surface == "hosting":
        document_url = "/api/hosting/v2/auto-runtime-guide.md"
    else:
        document_url = "/api/digital-assets/hosting-mechanisms/download"
    return {
        "ok": True,
        "version": STANDARD_VERSION,
        "schema": "warehouse.hosting-mechanisms.v2.3",
        "filename": AUTO_RUNTIME_GUIDE_FILENAME,
        "content": auto_runtime_guide_path().read_text(encoding="utf-8"),
        "downloads": [
            {
                "label": "下載《託管機制與 Auto Runtime 連接指南》",
                "name": AUTO_RUNTIME_GUIDE_FILENAME,
                "url": document_url,
                "filename": AUTO_RUNTIME_GUIDE_FILENAME,
                "media_type": "text/markdown",
            }
        ],
        "note": (
            "這份文件是 Auto Runtime 的設計與連接指南，不是額外授權；AI 必須依"
            "實時能力目錄、租戶 scope、確認策略和部署證據執行。"
        ),
    }


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
        "content": standard_path().read_text(encoding="utf-8"),
        "contract": contract,
        "downloads": requirement_downloads(public_surface=public_surface),
        "note": (
            "文件與機器契約使用同一版本；AI 應依 contract 回答並把 downloads "
            "原樣交給需要下載的使用者。"
        ),
    }
