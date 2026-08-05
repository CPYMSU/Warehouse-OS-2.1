from __future__ import annotations

import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from app.downloads.dam import _materialize_terminal_archive, _terminal_manifest_inputs

SOURCE_ID = "00000000-0000-0000-0000-000000000001"
SOURCE_SHA256 = "a" * 64


def _manifest(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "hosting_mode": "terminal",
        "execution_target": "user_terminal",
        "source_version_id": SOURCE_ID,
        "source_sha256": SOURCE_SHA256,
        "source_download": f"/api/workspaces/v1/sources/{SOURCE_ID}/download",
        "runtime": {"command": "do-not-run"},
    }
    value.update(overrides)
    return value


def test_terminal_manifest_is_bound_to_the_source_download_route() -> None:
    assert _terminal_manifest_inputs(_manifest()) == (SOURCE_ID, SOURCE_SHA256)

    with pytest.raises(SystemExit, match="路由"):
        _terminal_manifest_inputs(
            _manifest(source_download="https://attacker.example/source.tar.gz")
        )

    with pytest.raises(SystemExit, match="source_sha256"):
        _terminal_manifest_inputs(_manifest(source_sha256="not-a-digest"))


def test_zip_preparation_is_bounded_and_never_marks_execution(tmp_path: Path) -> None:
    archive = tmp_path / "source.archive"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr("app.py", "print('this is never run')\n")
        output.writestr("assets/index.html", "<h1>ready</h1>\n")

    destination = tmp_path / "source"
    prepared = _materialize_terminal_archive(archive, destination)

    assert prepared["format"] == "zip"
    assert prepared["files"] == 2
    assert prepared["executed"] is False
    assert (destination / "app.py").read_text() == "print('this is never run')\n"
    assert stat.S_IMODE((destination / "app.py").stat().st_mode) == 0o640


def test_archive_traversal_and_links_are_rejected_without_leaving_output(tmp_path: Path) -> None:
    traversal = tmp_path / "traversal.zip"
    with zipfile.ZipFile(traversal, "w") as output:
        output.writestr("../escape.txt", "no")
    traversal_destination = tmp_path / "traversal-out"
    with pytest.raises(SystemExit, match="不安全的路徑"):
        _materialize_terminal_archive(traversal, traversal_destination)
    assert not traversal_destination.exists()

    linked = tmp_path / "linked.tar"
    with tarfile.open(linked, "w") as output:
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        output.addfile(link)
    linked_destination = tmp_path / "linked-out"
    with pytest.raises(SystemExit, match="連結"):
        _materialize_terminal_archive(linked, linked_destination)
    assert not linked_destination.exists()


def test_archive_expansion_and_existing_destination_are_bounded(tmp_path: Path) -> None:
    archive = tmp_path / "large.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("app.py", "123456")
    with pytest.raises(SystemExit, match="展開後"):
        _materialize_terminal_archive(
            archive,
            tmp_path / "too-small",
            max_uncompressed_bytes=5,
        )

    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "keep.txt"
    sentinel.write_text("keep")
    with pytest.raises(SystemExit, match="已存在"):
        _materialize_terminal_archive(archive, existing)
    assert sentinel.read_text() == "keep"
