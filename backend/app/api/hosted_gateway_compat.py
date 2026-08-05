"""Small compatibility hooks for hosted application request semantics."""

from __future__ import annotations

import re


def rewrite_cookie_path(cookie: str, prefix: str) -> str:
    """Map every absolute application cookie path under the workspace entry."""

    clean_prefix = prefix.rstrip("/")
    match = re.search(r"(?i)(;\s*path=)(/[^;]*)", cookie)
    if match is None:
        return cookie + f"; Path={clean_prefix}/"
    original_path = match.group(2)
    if original_path == clean_prefix or original_path.startswith(clean_prefix + "/"):
        return cookie
    suffix = original_path if original_path.startswith("/") else "/" + original_path
    mapped = clean_prefix + suffix
    return cookie[: match.start(2)] + mapped + cookie[match.end(2) :]
