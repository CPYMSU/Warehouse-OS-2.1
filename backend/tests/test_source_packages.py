from __future__ import annotations

import io
import tarfile

from app.services.source_packages import (
    application_root,
    inspect_source_archive,
    materialize_source_archive,
)


def test_standard_tar_root_marker_is_accepted_and_materialized(tmp_path) -> None:
    archive_path = tmp_path / "site.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        root = tarfile.TarInfo(".")
        root.type = tarfile.DIRTYPE
        archive.addfile(root)
        for name, content in {
            "./index.html": b"<!doctype html><title>BIU CASEWORK</title>",
            "./app.js": b"globalThis.biu = true;",
        }.items():
            item = tarfile.TarInfo(name)
            item.size = len(content)
            archive.addfile(item, io.BytesIO(content))

    inspected = inspect_source_archive(
        archive_path,
        max_uncompressed_bytes=1024 * 1024,
    )
    assert inspected.files == 2
    assert inspected.signals["index_html"] is True
    assert inspected.signals["candidate_entrypoints"] == ["index.html"]

    destination = tmp_path / "release"
    materialize_source_archive(
        archive_path,
        destination,
        max_uncompressed_bytes=1024 * 1024,
    )
    assert application_root(destination).joinpath("index.html").is_file()
