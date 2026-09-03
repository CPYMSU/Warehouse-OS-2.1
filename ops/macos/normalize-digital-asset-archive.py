#!/usr/bin/env python3
"""Make subdirectory Git archives byte-stable before publishing.

`git archive <commit>:<subdir>` resolves to a tree object. Without an explicit
absolute timestamp Git writes the archive creation time. On the production Git
version, the shorthand `@0` is also interpreted as the current time, so it is
not reproducible. This normalizer uses an ISO-8601 epoch timestamp instead.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ORIGINAL = '["git", "archive", "--format=tar", f"--output={raw_tar}", treeish],'
BROKEN = '["git", "archive", "--format=tar", "--mtime=@0", f"--output={raw_tar}", treeish],'
STABLE = '["git", "archive", "--format=tar", "--mtime=1970-01-01T00:00:00Z", f"--output={raw_tar}", treeish],'


def normalize(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    original_count = text.count(ORIGINAL)
    broken_count = text.count(BROKEN)
    stable_count = text.count(STABLE)

    if stable_count == 1 and original_count == 0 and broken_count == 0:
        return {
            "ok": True,
            "changed": False,
            "path": str(path),
            "mtime": "1970-01-01T00:00:00Z",
        }

    if stable_count == 0 and original_count + broken_count == 1:
        source = ORIGINAL if original_count == 1 else BROKEN
        path.write_text(text.replace(source, STABLE, 1), encoding="utf-8")
        return {
            "ok": True,
            "changed": True,
            "path": str(path),
            "mtime": "1970-01-01T00:00:00Z",
        }

    raise RuntimeError(
        "unexpected git archive signature: "
        f"original={original_count} broken={broken_count} stable={stable_count} path={path}"
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
