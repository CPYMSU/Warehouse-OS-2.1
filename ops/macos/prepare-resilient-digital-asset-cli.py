#!/usr/bin/env python3
"""Download and harden the Warehouse digital-asset CLI for unstable links.

The generated CLI is still the server-provided client. This runner-side step
only adds bounded retries and longer read timeouts to idempotent JSON requests
and resumable source-part uploads. It does not change API paths or credentials.
"""

from __future__ import annotations

import argparse
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

REQUEST_OLD = '''        try:
            with urllib.request.urlopen(request, body, timeout=30) as response:
                value = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                error = json.loads(raw)
                detail = error.get("detail") or error.get("error") or error
                message = (
                    json.dumps(detail, ensure_ascii=False)
                    if isinstance(detail, (dict, list))
                    else str(detail)
                )
            except (json.JSONDecodeError, AttributeError):
                message = raw or exc.reason
            raise SystemExit(f"HTTP {exc.code}：{message}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"無法連接 {self.base}：{exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise SystemExit("服務端沒有返回合法 JSON") from exc
'''

REQUEST_NEW = '''        # Warehouse resilient request retry: the endpoints used by this CLI are
        # idempotent or carry server-side idempotency keys.
        value = None
        last_error = None
        for attempt in range(1, 7):
            try:
                with urllib.request.urlopen(request, body, timeout=180) as response:
                    value = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", "replace")
                try:
                    error = json.loads(raw)
                    detail = error.get("detail") or error.get("error") or error
                    message = (
                        json.dumps(detail, ensure_ascii=False)
                        if isinstance(detail, (dict, list))
                        else str(detail)
                    )
                except (json.JSONDecodeError, AttributeError):
                    message = raw or exc.reason
                if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt >= 6:
                    raise SystemExit(f"HTTP {exc.code}：{message}") from exc
                last_error = exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt >= 6:
                    reason = getattr(exc, "reason", exc)
                    raise SystemExit(f"無法連接 {self.base}：{reason}") from exc
                last_error = exc
            except json.JSONDecodeError as exc:
                raise SystemExit("服務端沒有返回合法 JSON") from exc
            time.sleep(min(2 ** attempt, 20))
        if value is None:
            raise SystemExit(f"服務請求重試後仍失敗：{last_error}")
'''

PART_OLD = '''            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    value = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", "replace")
                raise RuntimeError(f"分片 {part_no} HTTP {exc.code}：{raw}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"分片 {part_no} 連接失敗：{exc.reason}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"分片 {part_no} 返回格式錯誤")
'''

PART_NEW = '''            # Warehouse resilient part retry: each part is content-addressed and
            # can be replayed safely after a timeout.
            value = None
            last_error = None
            for attempt in range(1, 7):
                try:
                    with urllib.request.urlopen(request, timeout=180) as response:
                        value = json.loads(response.read().decode("utf-8"))
                    break
                except urllib.error.HTTPError as exc:
                    raw = exc.read().decode("utf-8", "replace")
                    if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt >= 6:
                        raise RuntimeError(f"分片 {part_no} HTTP {exc.code}：{raw}") from exc
                    last_error = exc
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    if attempt >= 6:
                        reason = getattr(exc, "reason", exc)
                        raise RuntimeError(f"分片 {part_no} 連接失敗：{reason}") from exc
                    last_error = exc
                time.sleep(min(2 ** attempt, 20))
            if value is None:
                raise RuntimeError(f"分片 {part_no} 重試後仍失敗：{last_error}")
            if not isinstance(value, dict):
                raise RuntimeError(f"分片 {part_no} 返回格式錯誤")
'''


def download(url: str) -> bytes:
    last_error: BaseException | None = None
    for attempt in range(1, 7):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Warehouse-MacRunner-CLI-Preparer/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= 6:
                break
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"failed to download digital-asset CLI after retries: {last_error}")


def replace_once(text: str, old: str, new: str, marker: str) -> str:
    if marker in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"unexpected CLI signature for {marker}: count={count}")
    return text.replace(old, new, 1)


def prepare(target: Path, base_url: str) -> None:
    raw = download(base_url.rstrip("/") + "/api/digital-assets/cli")
    text = raw.decode("utf-8")
    text = replace_once(text, REQUEST_OLD, REQUEST_NEW, "Warehouse resilient request retry")
    text = replace_once(text, PART_OLD, PART_NEW, "Warehouse resilient part retry")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(target)
    print(
        f"prepared resilient digital-asset CLI: path={target} bytes={target.stat().st_size}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("WAREHOUSE_BASE_URL") or "https://bonfirework.org",
    )
    args = parser.parse_args()
    prepare(args.target.expanduser(), str(args.base_url))


if __name__ == "__main__":
    main()
