from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.task_collaboration import _image_dimensions
from app.services.task_collaboration_documents import (
    _apply_operations,
    _normalise_operations,
    _public_snapshot,
    _snapshot_nodes,
)


def test_rga_concurrent_siblings_converge_without_overwriting() -> None:
    first, _, _ = _apply_operations(
        {},
        _normalise_operations(
            [{"type": "insert", "id": "alice:1", "after": "^", "value": "甲", "clock": 1}]
        ),
    )
    merged, content, changed = _apply_operations(
        first,
        _normalise_operations(
            [{"type": "insert", "id": "bob:1", "after": "^", "value": "乙", "clock": 1}]
        ),
    )
    assert changed is True
    assert content == "乙甲"
    assert set(merged) == {"alice:1", "bob:1"}


def test_public_snapshot_retains_tombstone_topology_without_deleted_text() -> None:
    nodes, _, _ = _apply_operations(
        {},
        _normalise_operations(
            [{"type": "insert", "id": "writer:1", "after": "^", "value": "字", "clock": 1}]
        ),
    )
    deleted, content, _ = _apply_operations(
        nodes, _normalise_operations([{"type": "delete", "id": "writer:1"}])
    )
    public = _public_snapshot(deleted)
    assert content == ""
    assert public["nodes"][0]["value"] == ""
    assert public["nodes"][0]["deleted"] is True


def test_snapshot_rejects_cycles() -> None:
    with pytest.raises(HTTPException, match="corrupt"):
        _snapshot_nodes(
            {
                "format": "rga-v1",
                "nodes": [
                    {"id": "a", "after": "b", "value": "a", "clock": 1, "deleted": False},
                    {"id": "b", "after": "a", "value": "b", "clock": 2, "deleted": False},
                ],
            }
        )


def test_png_dimensions_are_bounded_and_mime_checked() -> None:
    png = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\x0dIHDR"
        + (640).to_bytes(4, "big")
        + (480).to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )
    assert _image_dimensions(png, "image/png") == (640, 480)
    with pytest.raises(HTTPException):
        _image_dimensions(png, "image/jpeg")
