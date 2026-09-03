#!/usr/bin/env python3
"""Make subdirectory Git archives byte-stable before installing the publisher.

`git archive <commit>:<subdir>` resolves to a tree object, whose default mtime is
the archive creation time. Injecting `--mtime=@0` makes repeated packages for the
same source commit identical. The transformation is narrow and idempotent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

OLD = '["git", "archive", "--format=tar", f"--output={raw_tar}", treeish],'
NEW = '["git", "archive", "--format=tar", "--mtime=@0", f"--output={raw_tar}", treeish],'


def normalize(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    occurrences = text.count(OLD)
    normalized = text.count(NEW)
    if occurrences == 1 and normalized == 0:
        path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
        return {"ok": True, "changed": True, "path": str(path), "mtime": "@0"}
    if occurrences == 0 and normalized == 1:
        return {"ok": True, "changed": False, "path": str(path), "mtime": "@0"}
    raise RuntimeError(
        f"unexpected git archive signature: old={occurrences} normalized={normalized} path={path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("publish-digital-assets.py"),
    )
    args = parser.parse_args()
    print(json.dumps(normalize(args.path), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
