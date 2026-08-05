#!/usr/bin/env python3
"""dm.py 2.6.0 — Warehouse OS 智能數字資產託管客戶端。

這個版本只呼叫 Warehouse OS 2.1 原生端點：
  GET /api/workspaces/v1/info
  GET /api/workspaces/v1/usage
  GET /api/workspaces/v1/database/schema
  GET /api/workspaces/v1/data/{collection}
  PUT /api/workspaces/v1/data/{collection}/{record_key}
  POST /api/workspaces/v1/sources/upload
  GET  /api/workspaces/v1/sources
  GET  /api/workspaces/v1/sources/{id}/download
  PUT  /api/workspaces/v1/runtime
  POST /api/workspaces/v1/storage/probe
  POST /api/workspaces/v1/deployments
  POST /api/workspaces/v1/jobs
  GET|PUT /api/workspaces/v1/database/control|policy
  GET  /api/workspaces/v1/deployments[/{id}]
  GET  /api/hosting/v2/manifest
  GET  /api/hosting/v2/auto-runtime-guide.md
  GET  /api/hosting/v2/requirements
  GET  /api/hosting/v2/hosting
  GET  /api/hosting/v2/notifications
  GET  /api/hosting/v2/compute-usage
  POST /api/hosting/v2/notifications/{id}/ack
  GET  /api/hosting/v2/terminal-actions/{id}
  POST /api/hosting/v2/terminal-actions/{id}/complete
  POST /api/hosting/v2/sessions[/{id}/messages]
  GET  /api/hosting/v2/sessions/{id}[/events]
  GET  /api/workspaces/v1/fabric/manifest
  GET  /api/workspaces/v1/fabric
  POST /api/workspaces/v1/fabric/resources
  GET  /api/workspaces/v1/fabric/actions/{id}

認證使用 wak_ 工作區 Key。Key 可放在 WAREHOUSE_WORKSPACE_KEY；服務地址可放在
WAREHOUSE_BASE_URL。CLI 不提供 2.0 的 SQLite 或 raw SQL 命令。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath

VERSION = "2.6.0"
DEFAULT_BASE = "__WAREHOUSE_BASE__"

# ``hosting prepare`` is deliberately a preparation boundary, not an
# execution boundary.  Keep the local expansion limits in the standalone
# client so a hostile/misconfigured archive cannot turn a manifest download
# into an unbounded disk write.  These limits match the default Warehouse
# workspace quota and the server-side source-package validator.
MAX_TERMINAL_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_TERMINAL_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_TERMINAL_ARCHIVE_ENTRIES = 20_000
MAX_TERMINAL_COMPRESSION_RATIO = 200
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _terminal_manifest_inputs(manifest: object) -> tuple[str, str]:
    """Validate the least-privilege terminal manifest before downloading.

    The source route is checked against the source id instead of being
    treated as an arbitrary URL.  Runtime commands are intentionally not
    interpreted here; this helper only returns the immutable source identity
    and digest needed for a safe local preparation.
    """

    if not isinstance(manifest, dict):
        raise SystemExit("終端 Manifest 格式錯誤：預期 JSON 物件")
    if str(manifest.get("hosting_mode") or "").lower() != "terminal":
        raise SystemExit("終端 Manifest 不是 terminal hosting")
    if str(manifest.get("execution_target") or "").lower() != "user_terminal":
        raise SystemExit("終端 Manifest 的 execution_target 不受信任")
    source_id = str(manifest.get("source_version_id") or "").strip()
    if not source_id or not _SOURCE_ID_RE.fullmatch(source_id):
        raise SystemExit("終端 Manifest 缺少有效的 source_version_id")
    source_sha256 = str(manifest.get("source_sha256") or "").strip().lower()
    if not _SHA256_RE.fullmatch(source_sha256):
        raise SystemExit("終端 Manifest 缺少有效的 source_sha256")
    expected_route = (
        f"/api/workspaces/v1/sources/{urllib.parse.quote(source_id, safe='')}/download"
    )
    if str(manifest.get("source_download") or "") != expected_route:
        raise SystemExit("終端 Manifest 的 source_download 路由不受信任")
    return source_id, source_sha256


def _safe_archive_member(name: str) -> PurePosixPath:
    """Return a normalized archive member path or reject traversal/special paths."""

    normalized = str(name).replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or "\x00" in normalized
        or normalized.startswith("/")
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(len(part) == 2 and part[1] == ":" for part in path.parts[:1])
    ):
        raise SystemExit("源碼壓縮包包含不安全的路徑")
    return path


def _safe_archive_target(root: Path, member: PurePosixPath) -> Path:
    """Resolve a member beneath a newly-created extraction root."""

    root_resolved = root.resolve()
    target = root.joinpath(*member.parts)
    resolved = target.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise SystemExit("源碼壓縮包路徑跳出準備目錄")
    return target


def _materialize_terminal_archive(
    archive_path: Path,
    destination: Path,
    *,
    max_archive_bytes: int = MAX_TERMINAL_ARCHIVE_BYTES,
    max_uncompressed_bytes: int = MAX_TERMINAL_UNCOMPRESSED_BYTES,
) -> dict[str, object]:
    """Safely unpack a ZIP/TAR for inspection; never invokes its commands.

    Archive links, devices and FIFOs are rejected.  The destination must not
    already exist, so rerunning preparation cannot delete or overwrite a
    user's files.  Every output file is written with non-executable mode.
    """

    archive_path = archive_path.expanduser().resolve()
    if not archive_path.is_file():
        raise SystemExit(f"找不到源碼壓縮包：{archive_path}")
    packed_bytes = archive_path.stat().st_size
    if packed_bytes > max_archive_bytes:
        raise SystemExit("源碼壓縮包超過本機準備大小限制")
    destination = destination.expanduser().resolve()
    if destination.exists():
        raise SystemExit(f"準備目錄已存在，為避免覆寫而停止：{destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(mode=0o750)

    entries = 0
    files = 0
    unpacked = 0
    seen: set[str] = set()
    archive_format: str

    def begin_member(name: str, *, is_directory: bool) -> tuple[PurePosixPath, Path] | None:
        nonlocal entries
        entries += 1
        if entries > MAX_TERMINAL_ARCHIVE_ENTRIES:
            raise SystemExit("源碼壓縮包包含過多檔案項目")
        raw_name = name.rstrip("/")
        if raw_name in {"", "."} and is_directory:
            return None
        member = _safe_archive_member(raw_name)
        key = member.as_posix()
        if key in seen:
            raise SystemExit("源碼壓縮包包含重複路徑")
        seen.add(key)
        return member, _safe_archive_target(destination, member)

    def check_size(size: int) -> None:
        nonlocal unpacked
        if size < 0 or unpacked + size > max_uncompressed_bytes:
            raise SystemExit("源碼壓縮包展開後超過本機準備大小限制")
        unpacked += size

    try:
        if zipfile.is_zipfile(archive_path):
            archive_format = "zip"
            with zipfile.ZipFile(archive_path) as archive:
                for item in archive.infolist():
                    mode = item.external_attr >> 16
                    if stat.S_ISLNK(mode):
                        raise SystemExit("源碼壓縮包不得包含符號連結")
                    prepared = begin_member(item.filename, is_directory=item.is_dir())
                    if prepared is None:
                        continue
                    member, target = prepared
                    if item.is_dir():
                        if target.exists():
                            if not target.is_dir():
                                raise SystemExit("源碼壓縮包路徑類型衝突")
                        else:
                            target.mkdir(parents=True, exist_ok=False, mode=0o750)
                        continue
                    if stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
                        raise SystemExit("源碼壓縮包不得包含特殊檔案")
                    declared_size = int(item.file_size)
                    check_size(declared_size)
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
                    with archive.open(item) as source, target.open("xb") as output:
                        copied = 0
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            copied += len(chunk)
                            if copied > declared_size or copied > max_uncompressed_bytes:
                                raise SystemExit("源碼壓縮包展開長度不符合宣告")
                            output.write(chunk)
                    if copied != declared_size:
                        raise SystemExit("源碼壓縮包檔案長度不符合宣告")
                    target.chmod(0o640)
                    files += 1
        elif tarfile.is_tarfile(archive_path):
            archive_format = "tar"
            with tarfile.open(archive_path, mode="r:*") as archive:
                for item in archive:
                    if item.issym() or item.islnk() or item.isdev() or item.isfifo():
                        raise SystemExit("源碼壓縮包不得包含連結或特殊檔案")
                    prepared = begin_member(item.name, is_directory=item.isdir())
                    if prepared is None:
                        continue
                    _member, target = prepared
                    if item.isdir():
                        if target.exists():
                            if not target.is_dir():
                                raise SystemExit("源碼壓縮包路徑類型衝突")
                        else:
                            target.mkdir(parents=True, exist_ok=False, mode=0o750)
                        continue
                    if not item.isfile():
                        raise SystemExit("源碼壓縮包包含不支援的檔案類型")
                    declared_size = int(item.size)
                    check_size(declared_size)
                    source = archive.extractfile(item)
                    if source is None:
                        raise SystemExit("源碼壓縮包檔案無法讀取")
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
                    with source, target.open("xb") as output:
                        copied = 0
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            copied += len(chunk)
                            if copied > declared_size or copied > max_uncompressed_bytes:
                                raise SystemExit("源碼壓縮包展開長度不符合宣告")
                            output.write(chunk)
                    if copied != declared_size:
                        raise SystemExit("源碼壓縮包檔案長度不符合宣告")
                    target.chmod(0o640)
                    files += 1
        else:
            raise SystemExit("源碼必須是 ZIP 或 TAR 壓縮包")
    except BaseException:
        # The destination was created solely by this bounded preparation.  It
        # is safe to clean it on a failed extraction; pre-existing user paths
        # were rejected before creation.
        shutil.rmtree(destination, ignore_errors=True)
        raise

    if files == 0:
        shutil.rmtree(destination, ignore_errors=True)
        raise SystemExit("源碼壓縮包不包含檔案")
    if unpacked > max(1, packed_bytes) * MAX_TERMINAL_COMPRESSION_RATIO:
        shutil.rmtree(destination, ignore_errors=True)
        raise SystemExit("源碼壓縮包展開比例不安全")
    return {
        "format": archive_format,
        "entries": entries,
        "files": files,
        "uncompressed_bytes": unpacked,
        "directory": str(destination),
        "executed": False,
    }


def _json_object(raw: str, *, source: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{source} 不是合法 JSON：{exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{source} 必須是 JSON 物件")
    return value


def _payload(args: argparse.Namespace) -> dict[str, object]:
    if args.data is not None:
        return _json_object(args.data, source="--data")
    if args.file is not None:
        if args.file == "-":
            return _json_object(sys.stdin.read(), source="stdin")
        path = Path(args.file)
        if not path.is_file():
            raise SystemExit(f"找不到 JSON 文件：{path}")
        return _json_object(path.read_text(encoding="utf-8"), source=str(path))
    raise SystemExit("put 需要 --data '<JSON物件>' 或 --file <JSON文件>")


class Client:
    def __init__(self, base: str, key: str) -> None:
        self.base = base.rstrip("/")
        self.key = key.strip()
        if not self.base.startswith(("http://", "https://")):
            raise SystemExit("服務地址必須以 http:// 或 https:// 開頭")
        if not self.key.startswith("wak_"):
            raise SystemExit("需要 Warehouse OS 2.1 的 wak_ 工作區 Key")

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, object]:
        url = self.base + path
        clean_query = {key: value for key, value in (query or {}).items() if value is not None}
        if clean_query:
            url += "?" + urllib.parse.urlencode(clean_query)
        request = urllib.request.Request(url, method=method)
        request.add_header("Authorization", "Bearer " + self.key)
        request.add_header("Accept", "application/json")
        request.add_header("User-Agent", f"WarehouseOS-dam/{VERSION}")
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request.add_header("Content-Type", "application/json; charset=utf-8")
        try:
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
        if not isinstance(value, dict):
            raise SystemExit("服務端返回格式錯誤：預期 JSON 物件")
        return value

    def upload_source(
        self,
        path: Path,
        *,
        version: str | None,
        component: str | None,
    ) -> dict[str, object]:
        if not path.is_file():
            raise SystemExit(f"找不到源碼壓縮包：{path}")
        boundary = "warehouse-" + uuid.uuid4().hex
        fields = {"version_no": version, "component": component}
        chunks: list[bytes] = []
        for name, value in fields.items():
            if value is None:
                continue
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )
        content = path.read_bytes()
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                ).encode(),
                b"Content-Type: application/octet-stream\r\n\r\n",
                content,
                b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )
        body = b"".join(chunks)
        request = urllib.request.Request(
            self.base + "/api/workspaces/v1/sources/upload",
            data=body,
            method="POST",
            headers={
                "Authorization": "Bearer " + self.key,
                "Accept": "application/json",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-SHA256": hashlib.sha256(content).hexdigest(),
                "User-Agent": f"WarehouseOS-dam/{VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                value = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            raise SystemExit(f"HTTP {exc.code}：{raw}") from exc
        if not isinstance(value, dict):
            raise SystemExit("服務端返回格式錯誤：預期 JSON 物件")
        return value

    def upload_hosting_source(
        self,
        session_id: str,
        path: Path,
        *,
        version: str | None,
        component: str | None,
    ) -> dict[str, object]:
        if not path.is_file():
            raise SystemExit(f"找不到源碼壓縮包：{path}")
        boundary = "warehouse-" + uuid.uuid4().hex
        chunks: list[bytes] = []
        for name, value in {"version_no": version, "component": component}.items():
            if value is None:
                continue
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )
        content = path.read_bytes()
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                ).encode(),
                b"Content-Type: application/octet-stream\r\n\r\n",
                content,
                b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )
        body = b"".join(chunks)
        safe_session = urllib.parse.quote(session_id, safe="")
        request = urllib.request.Request(
            self.base + f"/api/hosting/v2/sessions/{safe_session}/sources",
            data=body,
            method="POST",
            headers={
                "Authorization": "Bearer " + self.key,
                "Accept": "application/json",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-SHA256": hashlib.sha256(content).hexdigest(),
                "User-Agent": f"WarehouseOS-dm/{VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                value = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            raise SystemExit(f"HTTP {exc.code}：{raw}") from exc
        if not isinstance(value, dict):
            raise SystemExit("服務端返回格式錯誤：預期 JSON 物件")
        return value

    def download_source(
        self,
        source_id: str,
        output: Path | None,
        *,
        expected_sha256: str | None = None,
        max_bytes: int | None = None,
        overwrite: bool = True,
    ) -> dict[str, object]:
        safe_source = urllib.parse.quote(source_id, safe="")
        request = urllib.request.Request(
            self.base + f"/api/workspaces/v1/sources/{safe_source}/download",
            method="GET",
            headers={
                "Authorization": "Bearer " + self.key,
                "Accept": "application/octet-stream",
                "User-Agent": f"WarehouseOS-dam/{VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                disposition = response.headers.get("Content-Disposition", "")
                filename_match = re.search(r'filename="?([^";]+)', disposition)
                remote_name = Path(
                    urllib.parse.unquote(filename_match.group(1))
                    if filename_match
                    else f"source-{source_id}.tar.gz"
                ).name
                target = output or Path(remote_name)
                if target.is_dir():
                    target = target / remote_name
                target = target.expanduser().resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and not overwrite:
                    raise SystemExit(f"輸出檔案已存在，為避免覆寫而停止：{target}")
                temporary = target.with_name(target.name + ".part")
                digest = hashlib.sha256()
                size = 0
                try:
                    with temporary.open("wb") as destination:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            if max_bytes is not None and size + len(chunk) > max_bytes:
                                raise SystemExit("下載源碼超過本機準備大小限制")
                            destination.write(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                    expected = str(response.headers.get("Content-SHA256") or "").lower()
                    actual = digest.hexdigest()
                    if expected and expected != actual:
                        raise SystemExit(
                            f"下載 SHA-256 不一致：expected={expected} actual={actual}"
                        )
                    if expected_sha256 and expected_sha256.lower() != actual:
                        raise SystemExit(
                            "下載 SHA-256 不一致："
                            f"expected={expected_sha256.lower()} actual={actual}"
                        )
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            raise SystemExit(f"HTTP {exc.code}：{raw}") from exc
        return {
            "ok": True,
            "source_version_id": source_id,
            "path": str(target),
            "size_bytes": size,
            "sha256": actual,
        }

    def terminal_manifest(self, deployment_id: str) -> dict[str, object]:
        safe_deployment = urllib.parse.quote(deployment_id, safe="")
        return self.request("GET", f"/api/hosting/v2/terminal-actions/{safe_deployment}")

    def download_text(
        self,
        path: str,
        *,
        output: Path | None = None,
        default_filename: str = "warehouse-guide.md",
        max_bytes: int = 8 * 1024 * 1024,
    ) -> dict[str, object]:
        """Download a UTF-8 document without making ``request`` parse Markdown.

        With no output path the command returns only safe metadata, avoiding a
        large document being copied into a shell/AI transcript.  Passing an
        explicit output path writes the verified bytes locally and returns the
        path and digest.  This method is read-only from the Warehouse API's
        perspective; it never submits a session or mutates hosting state.
        """

        if not path.startswith("/") or "?" in path or "#" in path:
            raise SystemExit("文件下载路径必须是同源的绝对 API 路径")
        request = urllib.request.Request(
            self.base + path,
            method="GET",
            headers={
                "Authorization": "Bearer " + self.key,
                "Accept": "text/markdown, text/plain;q=0.9, */*;q=0.1",
                "User-Agent": f"WarehouseOS-dam/{VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content_type = str(response.headers.get_content_type() or "text/plain")
                disposition = response.headers.get("Content-Disposition", "")
                filename_match = re.search(r'filename="?([^";]+)', disposition)
                remote_name = Path(
                    urllib.parse.unquote(filename_match.group(1))
                    if filename_match
                    else default_filename
                ).name
                chunks: list[bytes] = []
                size = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise SystemExit("文件下载超过本地大小限制")
                    chunks.append(chunk)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(raw)
                detail = detail.get("detail") or detail.get("error") or detail
                message = (
                    json.dumps(detail, ensure_ascii=False)
                    if isinstance(detail, (dict, list))
                    else str(detail)
                )
            except (json.JSONDecodeError, AttributeError):
                message = raw or str(exc.reason)
            raise SystemExit(f"HTTP {exc.code}：{message}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"無法連接 {self.base}：{exc.reason}") from exc

        content = b"".join(chunks)
        digest = hashlib.sha256(content).hexdigest()
        result: dict[str, object] = {
            "ok": True,
            "source": path,
            "filename": remote_name,
            "media_type": content_type,
            "size_bytes": len(content),
            "sha256": digest,
            "downloaded": output is not None,
        }
        if output is not None:
            target = output.expanduser().resolve()
            if target.exists() and target.is_dir():
                raise SystemExit(f"输出路径是目录，请指定文件：{target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".part")
            try:
                with temporary.open("xb") as destination:
                    destination.write(content)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            result["path"] = str(target)
        return result


def _show(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dm.py",
        description="Warehouse OS 2.3 智能數字資產託管與 Data API 客戶端",
    )
    parser.add_argument(
        "--base",
        default=os.environ.get("WAREHOUSE_BASE_URL") or DEFAULT_BASE,
        help="Warehouse OS 服務地址（或設 WAREHOUSE_BASE_URL）",
    )
    parser.add_argument(
        "--key",
        default=os.environ.get("WAREHOUSE_WORKSPACE_KEY"),
        help="wak_ 工作區 Key（建議改設 WAREHOUSE_WORKSPACE_KEY）",
    )
    parser.add_argument("--version", action="version", version=f"dam.py {VERSION}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("info", help="查看工作區、組件、數據庫及本 Key 的作用域")
    commands.add_parser("usage", help="刷新並查看源碼、Runtime、DATA 與 PostgreSQL 佔用")

    schema = commands.add_parser("schema", help="查看 Data API 的集合與記錄數")
    schema.add_argument("--database", help="指定邏輯數據庫；省略時使用第一個 ready 數據庫")

    listing = commands.add_parser("list", help="分頁讀取一個集合的記錄")
    listing.add_argument("collection", help="集合名稱，例如 customers")
    listing.add_argument("--database", help="指定邏輯數據庫")
    listing.add_argument(
        "--limit",
        type=int,
        default=100,
        choices=range(1, 1001),
        metavar="1..1000",
    )
    listing.add_argument("--offset", type=int, default=0)

    put = commands.add_parser("put", help="新增或更新一筆 JSON 記錄")
    put.add_argument("collection", help="集合名稱，例如 customers")
    put.add_argument("record_key", help="穩定記錄鍵，例如 acme")
    source = put.add_mutually_exclusive_group(required=True)
    source.add_argument("--data", help="JSON 物件字串")
    source.add_argument("--file", help="JSON 文件；- 代表 stdin")
    put.add_argument("--database", help="指定邏輯數據庫")
    put.add_argument(
        "--expected-version",
        type=int,
        help="樂觀鎖版本；新記錄用 0，更新時使用上次返回的 version",
    )

    source_commands = commands.add_parser("source", help="管理不可變源碼版本")
    source_subcommands = source_commands.add_subparsers(dest="source_command", required=True)
    source_subcommands.add_parser("list", help="列出已驗證源碼版本")
    push = source_subcommands.add_parser("push", help="上傳 ZIP/TAR 源碼壓縮包")
    push.add_argument("archive", help="ZIP/TAR 源碼壓縮包")
    push.add_argument("--version", help="版本號，例如 v1.0.0")
    push.add_argument("--component", help="綁定的既有組件名稱")
    pull = source_subcommands.add_parser("pull", help="下載一個已驗證源碼版本")
    pull.add_argument("source_id", help="源碼 UUID 或列表中的數字 ID")
    pull.add_argument("--output", help="輸出檔案或既有目錄；省略時沿用遠端檔名")

    runtime_commands = commands.add_parser("runtime", help="辨識或設定部署 Runtime")
    runtime_subcommands = runtime_commands.add_subparsers(dest="runtime_command", required=True)
    runtime_subcommands.add_parser("show", help="查看目前 Runtime、組件與存儲狀態")
    runtime_set = runtime_subcommands.add_parser(
        "set", help="設定 static/web/api/worker/agent/job/container/compose，可同時提交部署"
    )
    runtime_set.add_argument(
        "--type",
        dest="runtime_type",
        choices=(
            "auto",
            "static",
            "web",
            "api",
            "worker",
            "agent",
            "job",
            "container",
            "compose",
        ),
        default="auto",
    )
    runtime_set.add_argument("--runtime", help="例如 static、python3.12、node20")
    runtime_set.add_argument("--profile", dest="runtime_profile")
    runtime_set.add_argument("--component")
    runtime_set.add_argument("--source", dest="source_version_id")
    runtime_set.add_argument("--entrypoint")
    runtime_set.add_argument("--build-command")
    runtime_set.add_argument("--start-command")
    runtime_set.add_argument("--health-path")
    runtime_set.add_argument("--image", help="OCI/Docker 映像；可與 Dockerfile 二選一")
    runtime_set.add_argument("--dockerfile", help="Dockerfile 相對路徑")
    runtime_set.add_argument("--compose-file", help="Compose 文件相對路徑")
    runtime_set.add_argument("--route-service", help="Compose 對外服務名稱")
    runtime_set.add_argument("--port", type=int, help="容器內 HTTP 端口")
    runtime_set.add_argument("--command", dest="container_command", help="覆寫容器啟動命令")
    runtime_set.add_argument("--deploy", action="store_true")
    runtime_set.add_argument(
        "--no-activate", dest="activate", action="store_false", default=True,
        help="建置並驗證，但不切換正式流量",
    )
    runtime_set.add_argument("--idempotency-key")

    storage_commands = commands.add_parser("storage", help="檢查工作區實際存儲")
    storage_subcommands = storage_commands.add_subparsers(dest="storage_command", required=True)
    storage_subcommands.add_parser("probe", help="修復缺失綁定並執行寫入、fsync、讀回及刪除探針")

    hosting_commands = commands.add_parser("hosting", help="讀取託管應用技術標準")
    hosting_subcommands = hosting_commands.add_subparsers(dest="hosting_command", required=True)
    hosting_subcommands.add_parser(
        "requirements",
        help="下載同版本的人類可讀標準與機器可讀契約",
    )
    hosting_guide = hosting_subcommands.add_parser(
        "guide",
        help="下載 cloud/terminal/hybrid 與 Auto Runtime AI 秘書連接指南",
    )
    hosting_guide.add_argument(
        "--output",
        type=Path,
        help="將指南保存到本地文件；省略時只輸出安全元數據",
    )
    hosting_subcommands.add_parser("mode", help="查看目前 cloud/terminal 托管模式")
    hosting_set = hosting_subcommands.add_parser("set", help="用智能接口切換托管模式")
    hosting_set.add_argument("mode", choices=("cloud", "terminal"))
    hosting_set.add_argument(
        "--compute-node",
        choices=("warehouse", "vultr", "mac_mini", "user_terminal"),
    )
    hosting_set.add_argument(
        "--notify-targets",
        help="terminal、ai 或逗號分隔的兩者",
    )
    hosting_set.add_argument("--cloud-fallback", choices=("ask", "never"))
    hosting_set.add_argument("--compute-budget", help="JSON 物件，例如 '{\"max_cost_cny\":20}'")
    hosting_notifications = hosting_subcommands.add_parser(
        "notifications", help="讀取終端或 AI 的托管提醒"
    )
    hosting_notifications.add_argument("--target", choices=("terminal", "ai"))
    hosting_notifications.add_argument(
        "--status",
        choices=("pending", "acknowledged", "expired", "cancelled"),
    )
    hosting_notifications.add_argument("--limit", type=int, default=100, choices=range(1, 501))
    hosting_subcommands.add_parser("usage", help="查看独立的云计算用量记录")
    hosting_ack = hosting_subcommands.add_parser("ack", help="確認一條托管提醒")
    hosting_ack.add_argument("notification_id")
    hosting_complete = hosting_subcommands.add_parser(
        "complete", help="提交終端執行結果，不啟動雲端 Runtime"
    )
    hosting_complete.add_argument("deployment_id")
    hosting_complete.add_argument("--status", choices=("succeeded", "failed"), default="succeeded")
    hosting_complete.add_argument("--result", help="結果 JSON 物件")
    hosting_complete.add_argument("--result-file", help="結果 JSON 文件；- 代表 stdin")
    hosting_action = hosting_subcommands.add_parser(
        "action", help="讀取一個終端部署的最小執行 Manifest"
    )
    hosting_action.add_argument("deployment_id")
    hosting_prepare = hosting_subcommands.add_parser(
        "prepare", help="下載並校驗終端部署源碼，不在本機自動執行"
    )
    hosting_prepare.add_argument("deployment_id")
    hosting_prepare.add_argument(
        "--directory",
        default=".warehouse-terminal",
        help="Manifest 與源碼壓縮包輸出目錄",
    )

    deploy_commands = commands.add_parser("deploy", help="提交及觀察部署")
    deploy_subcommands = deploy_commands.add_subparsers(dest="deploy_command", required=True)
    deploy_request = deploy_subcommands.add_parser(
        "request", help="自動校準 Runtime 並提交已驗證源碼版本"
    )
    deploy_request.add_argument("--source", dest="source_version_id")
    deploy_request.add_argument("--component")
    deploy_request.add_argument("--entrypoint")
    deploy_request.add_argument("--build-command")
    deploy_request.add_argument("--start-command")
    deploy_request.add_argument("--health-path")
    deploy_request.add_argument("--profile", dest="runtime_profile")
    deploy_request.add_argument("--idempotency-key")
    deploy_request.add_argument(
        "--no-activate", dest="activate", action="store_false", default=True,
        help="建立測試部署並保持目前 active 版本",
    )
    deploy_status = deploy_subcommands.add_parser("status", help="查看部署狀態")
    deploy_status.add_argument("deployment_id", nargs="?")
    deploy_logs = deploy_subcommands.add_parser("logs", help="查看部署事件與日誌")
    deploy_logs.add_argument("deployment_id")
    deploy_activate = deploy_subcommands.add_parser("activate", help="切換到既有 healthy 版本")
    deploy_activate.add_argument("deployment_id")
    deploy_accept = deploy_subcommands.add_parser(
        "accept", help="依源碼契約私網驗收 staged 版本"
    )
    deploy_accept.add_argument("deployment_id")

    job = commands.add_parser("job", help="執行不切換流量的受限一次性源碼任務")
    job.add_argument("--source", dest="source_version_id", required=True)
    job_selector = job.add_mutually_exclusive_group(required=True)
    job_selector.add_argument("--name", dest="job_name", help="manifest 聲明的 lifecycle job")
    job_selector.add_argument("--command", help="工作區邊界內的顯式一次性命令")
    job.add_argument("--component", default="job")
    job.add_argument("--runtime", help="例如 python3.12 或 node20")
    job.add_argument("--profile", dest="runtime_profile")
    job.add_argument("--entrypoint")
    job.add_argument("--build-command")
    job.add_argument("--database-url-env")
    job.add_argument(
        "--database-access",
        choices=("none", "runtime", "migration"),
        help="顯式命令的資料庫身份；聲明式 Job 由 manifest 決定",
    )
    job.add_argument("--timeout", dest="timeout_seconds", type=int, default=1200)
    job.add_argument("--idempotency-key")

    database = commands.add_parser("database", help="管理工作區資料庫生命週期策略與證據")
    database_subcommands = database.add_subparsers(dest="database_command", required=True)
    database_subcommands.add_parser("control", help="查看綁定、能力、備份、遷移與發布閘門")
    database_subcommands.add_parser("reconcile", help="重新核驗平台代管資料庫能力")
    database_policy = database_subcommands.add_parser("policy", help="選擇資料庫生命週期模式")
    database_policy.add_argument(
        "mode",
        choices=("platform_managed", "external", "workspace_managed", "none"),
    )

    agent_commands = commands.add_parser("agent", help="讓終端 AI 使用單一智能託管會話完成部署")
    agent_subcommands = agent_commands.add_subparsers(dest="agent_command", required=True)
    agent_subcommands.add_parser("manifest", help="讀取機器可理解的智能託管協議")
    agent_start = agent_subcommands.add_parser("start", help="建立智能託管會話")
    agent_start.add_argument("--message", required=True, help="自然語言託管目標")
    agent_start.add_argument(
        "--desired-state",
        help="desired_state JSON；終端 AI 應依 manifest 產生",
    )
    agent_start.add_argument("--execute", action="store_true", help="立即執行已提交意圖")
    agent_say = agent_subcommands.add_parser("say", help="向既有託管會話提交下一步")
    agent_say.add_argument("session_id")
    agent_say.add_argument("--message", required=True)
    agent_say.add_argument("--desired-state", help="desired_state JSON")
    agent_say.add_argument("--execute", action="store_true")
    agent_status = agent_subcommands.add_parser("status", help="查看並刷新真實託管狀態")
    agent_status.add_argument("session_id")
    agent_events = agent_subcommands.add_parser("events", help="查看可恢復的步驟與診斷事件")
    agent_events.add_argument("session_id")
    agent_events.add_argument("--after", type=int, default=0)
    agent_source = agent_subcommands.add_parser("source", help="向會話附加源碼壓縮包")
    agent_source.add_argument("session_id")
    agent_source.add_argument("archive")
    agent_source.add_argument("--version")
    agent_source.add_argument("--component")

    fabric_commands = commands.add_parser(
        "fabric", help="管理容器、域名、秘密、擴縮容、資料庫、Git、備份與 GPU 資源"
    )
    fabric_subcommands = fabric_commands.add_subparsers(dest="fabric_command", required=True)
    fabric_subcommands.add_parser("manifest", help="讀取可機器理解的資源類型與約束")
    fabric_subcommands.add_parser("show", help="觀察工作區所有資源與最近 action")
    fabric_apply = fabric_subcommands.add_parser("apply", help="建立或更新一個聲明式託管資源")
    fabric_apply.add_argument(
        "kind",
        choices=(
            "container",
            "compose",
            "domain",
            "environment",
            "secret",
            "scaling",
            "database_migration",
            "repository",
            "backup",
            "accelerator",
        ),
    )
    fabric_apply.add_argument("--resource-key", help="穩定資源鍵；省略時由服務端推導")
    fabric_spec = fabric_apply.add_mutually_exclusive_group(required=True)
    fabric_spec.add_argument("--spec", help="資源 spec JSON 物件")
    fabric_spec.add_argument("--spec-file", help="資源 spec JSON 文件；- 代表 stdin")
    fabric_apply.add_argument(
        "--preview", action="store_true", help="只驗證並記錄計畫，不執行外部副作用"
    )
    fabric_apply.add_argument("--idempotency-key", help="重試時使用相同值避免重複操作")
    fabric_action = fabric_subcommands.add_parser("action", help="查看 action 與事件")
    fabric_action.add_argument("action_id")
    return parser


def _fabric_spec(args: argparse.Namespace) -> dict[str, object]:
    if args.spec is not None:
        return _json_object(args.spec, source="--spec")
    if args.spec_file == "-":
        return _json_object(sys.stdin.read(), source="stdin")
    path = Path(args.spec_file)
    if not path.is_file():
        raise SystemExit(f"找不到 JSON 文件：{path}")
    return _json_object(path.read_text(encoding="utf-8"), source=str(path))


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if not args.key:
        parser.error("缺少工作區 Key；請設 WAREHOUSE_WORKSPACE_KEY 或使用 --key")
    client = Client(args.base, args.key)

    if args.command == "fabric":
        if args.fabric_command == "manifest":
            result = client.request("GET", "/api/workspaces/v1/fabric/manifest")
        elif args.fabric_command == "show":
            result = client.request("GET", "/api/workspaces/v1/fabric")
        elif args.fabric_command == "action":
            action_id = urllib.parse.quote(args.action_id, safe="")
            result = client.request("GET", f"/api/workspaces/v1/fabric/actions/{action_id}")
        else:
            result = client.request(
                "POST",
                "/api/workspaces/v1/fabric/resources",
                payload={
                    "kind": args.kind,
                    "resource_key": args.resource_key,
                    "spec": _fabric_spec(args),
                    "execute": not args.preview,
                },
                headers=(
                    {"Idempotency-Key": args.idempotency_key} if args.idempotency_key else None
                ),
            )
    elif args.command == "agent":
        if args.agent_command == "manifest":
            result = client.request("GET", "/api/hosting/v2/manifest")
        elif args.agent_command == "start":
            desired_state = (
                _json_object(args.desired_state, source="--desired-state")
                if args.desired_state
                else {}
            )
            result = client.request(
                "POST",
                "/api/hosting/v2/sessions",
                payload={
                    "message": args.message,
                    "client_kind": "terminal_ai",
                    "desired_state": desired_state,
                    "execute": args.execute,
                },
            )
        elif args.agent_command == "say":
            desired_state = (
                _json_object(args.desired_state, source="--desired-state")
                if args.desired_state
                else {}
            )
            session_id = urllib.parse.quote(args.session_id, safe="")
            result = client.request(
                "POST",
                f"/api/hosting/v2/sessions/{session_id}/messages",
                payload={
                    "message": args.message,
                    "desired_state": desired_state,
                    "execute": args.execute,
                },
            )
        elif args.agent_command == "status":
            session_id = urllib.parse.quote(args.session_id, safe="")
            result = client.request("GET", f"/api/hosting/v2/sessions/{session_id}")
        elif args.agent_command == "events":
            session_id = urllib.parse.quote(args.session_id, safe="")
            result = client.request(
                "GET",
                f"/api/hosting/v2/sessions/{session_id}/events",
                query={"after": args.after},
            )
        else:
            result = client.upload_hosting_source(
                args.session_id,
                Path(args.archive),
                version=args.version,
                component=args.component,
            )
    elif args.command == "hosting":
        if args.hosting_command == "guide":
            result = client.download_text(
                "/api/hosting/v2/auto-runtime-guide.md",
                output=args.output,
                default_filename="warehouse-hosting-mechanisms-2.3.zh-TW.md",
            )
        elif args.hosting_command == "requirements":
            result = client.request("GET", "/api/hosting/v2/requirements")
        elif args.hosting_command == "mode":
            result = client.request("GET", "/api/hosting/v2/hosting")
        elif args.hosting_command == "set":
            hosting = {
                key: value
                for key, value in {
                    "mode": args.mode,
                    "compute_node": args.compute_node,
                    "notify_targets": args.notify_targets,
                    "cloud_fallback": args.cloud_fallback,
                    "compute_budget": (
                        _json_object(args.compute_budget, source="--compute-budget")
                        if args.compute_budget
                        else None
                    ),
                }.items()
                if value is not None
            }
            result = client.request(
                "POST",
                "/api/hosting/v2/sessions",
                payload={
                    "message": f"Set hosting mode to {args.mode}",
                    "client_kind": "terminal_ai",
                    "desired_state": {"hosting": hosting},
                    "execute": True,
                },
            )
        elif args.hosting_command == "notifications":
            result = client.request(
                "GET",
                "/api/hosting/v2/notifications",
                query={"target": args.target, "status": args.status, "limit": args.limit},
            )
        elif args.hosting_command == "usage":
            result = client.request("GET", "/api/hosting/v2/compute-usage")
        elif args.hosting_command == "ack":
            notification_id = urllib.parse.quote(args.notification_id, safe="")
            result = client.request(
                "POST",
                f"/api/hosting/v2/notifications/{notification_id}/ack",
            )
        elif args.hosting_command == "action":
            result = client.terminal_manifest(args.deployment_id)
        elif args.hosting_command == "prepare":
            action = client.terminal_manifest(args.deployment_id)
            manifest = action.get("manifest")
            source_id, expected_sha256 = _terminal_manifest_inputs(manifest)
            directory = Path(args.directory).expanduser().resolve()
            directory.mkdir(parents=True, exist_ok=True)
            if not directory.is_dir():
                raise SystemExit(f"輸出路徑不是目錄：{directory}")
            archive_path = directory / f"source-{source_id}.archive"
            manifest_file = directory / "terminal-manifest.json"
            source_directory = directory / "source"
            if manifest_file.exists():
                raise SystemExit(f"Manifest 輸出檔案已存在，為避免覆寫而停止：{manifest_file}")
            if source_directory.exists():
                raise SystemExit(f"源碼準備目錄已存在，為避免覆寫而停止：{source_directory}")
            download = client.download_source(
                source_id,
                archive_path,
                expected_sha256=expected_sha256,
                max_bytes=MAX_TERMINAL_ARCHIVE_BYTES,
                overwrite=False,
            )
            prepared = _materialize_terminal_archive(archive_path, source_directory)
            record = {
                "manifest": manifest,
                "deployment": action.get("deployment"),
                "download": download,
                "prepared_source": prepared,
                "executed": False,
            }
            with manifest_file.open("x", encoding="utf-8") as output:
                json.dump(record, output, ensure_ascii=False, indent=2, default=str)
                output.write("\n")
            result = {
                "ok": True,
                "prepared": True,
                "manifest_file": str(manifest_file),
                "source_directory": str(source_directory),
                "download": download,
                "archive": str(archive_path),
                "executed": False,
                "next_action": "review_manifest_then_execute_in_a_sandbox",
            }
        else:
            if args.result and args.result_file:
                raise SystemExit("--result 與 --result-file 只能選一個")
            if args.result:
                terminal_result = _json_object(args.result, source="--result")
            elif args.result_file:
                raw = (
                    sys.stdin.read()
                    if args.result_file == "-"
                    else Path(args.result_file).read_text(encoding="utf-8")
                )
                terminal_result = _json_object(raw, source=args.result_file)
            else:
                terminal_result = {}
            deployment_id = urllib.parse.quote(args.deployment_id, safe="")
            result = client.request(
                "POST",
                f"/api/hosting/v2/terminal-actions/{deployment_id}/complete",
                payload={"status": args.status, "result": terminal_result},
            )
    elif args.command == "info":
        result = client.request("GET", "/api/workspaces/v1/info")
    elif args.command == "usage":
        result = client.request("GET", "/api/workspaces/v1/usage")
    elif args.command == "schema":
        result = client.request(
            "GET",
            "/api/workspaces/v1/database/schema",
            query={"database": args.database},
        )
    elif args.command == "list":
        collection = urllib.parse.quote(args.collection, safe="")
        result = client.request(
            "GET",
            f"/api/workspaces/v1/data/{collection}",
            query={
                "database": args.database,
                "limit": args.limit,
                "offset": args.offset,
            },
        )
    elif args.command == "put":
        collection = urllib.parse.quote(args.collection, safe="")
        record_key = urllib.parse.quote(args.record_key, safe="")
        result = client.request(
            "PUT",
            f"/api/workspaces/v1/data/{collection}/{record_key}",
            query={
                "database": args.database,
                "expected_version": args.expected_version,
            },
            payload={"data": _payload(args)},
        )
    elif args.command == "source":
        if args.source_command == "list":
            result = client.request("GET", "/api/workspaces/v1/sources")
        elif args.source_command == "pull":
            result = client.download_source(
                args.source_id,
                Path(args.output) if args.output else None,
            )
        else:
            result = client.upload_source(
                Path(args.archive),
                version=args.version,
                component=args.component,
            )
    elif args.command == "runtime":
        if args.runtime_command == "show":
            result = client.request("GET", "/api/workspaces/v1/info")
        else:
            runtime_payload = {
                key: value
                for key, value in {
                    "runtime_type": args.runtime_type,
                    "runtime": args.runtime,
                    "runtime_profile": args.runtime_profile,
                    "component": args.component,
                    "source_version_id": args.source_version_id,
                    "entrypoint": args.entrypoint,
                    "build_command": args.build_command,
                    "start_command": args.start_command,
                    "health_path": args.health_path,
                    "image": args.image,
                    "dockerfile": args.dockerfile,
                    "compose_file": args.compose_file,
                    "route_service": args.route_service,
                    "port": args.port,
                    "command": args.container_command,
                    "deploy": args.deploy,
                    "activate": args.activate,
                    "idempotency_key": args.idempotency_key,
                }.items()
                if value is not None
            }
            result = client.request("PUT", "/api/workspaces/v1/runtime", payload=runtime_payload)
    elif args.command == "storage":
        result = client.request("POST", "/api/workspaces/v1/storage/probe")
    elif args.command == "database":
        if args.database_command == "control":
            result = client.request("GET", "/api/workspaces/v1/database/control")
        elif args.database_command == "reconcile":
            result = client.request("POST", "/api/workspaces/v1/database/reconcile")
        else:
            result = client.request(
                "PUT",
                "/api/workspaces/v1/database/policy",
                payload={"mode": args.mode},
            )
    elif args.command == "job":
        job_payload = {
            key: value
            for key, value in {
                "source_version_id": args.source_version_id,
                "job": args.job_name,
                "command": args.command,
                "component": args.component,
                "runtime": args.runtime,
                "runtime_profile": args.runtime_profile,
                "entrypoint": args.entrypoint,
                "build_command": args.build_command,
                "database_url_env": args.database_url_env,
                "database_access": args.database_access,
                "timeout_seconds": args.timeout_seconds,
            }.items()
            if value is not None
        }
        result = client.request(
            "POST",
            "/api/workspaces/v1/jobs",
            payload=job_payload,
            headers=(
                {"Idempotency-Key": args.idempotency_key}
                if args.idempotency_key
                else None
            ),
        )
    elif args.deploy_command == "request":
        deployment_payload = {
            key: value
            for key, value in {
                "source_version_id": args.source_version_id,
                "component": args.component,
                "entrypoint": args.entrypoint,
                "build_command": args.build_command,
                "start_command": args.start_command,
                "health_path": args.health_path,
                "runtime_profile": args.runtime_profile,
                "idempotency_key": args.idempotency_key,
                "activate": args.activate,
            }.items()
            if value is not None
        }
        result = client.request(
            "POST",
            "/api/workspaces/v1/deployments",
            payload=deployment_payload,
        )
    elif args.deploy_command == "status":
        path = "/api/workspaces/v1/deployments"
        if args.deployment_id:
            path += "/" + urllib.parse.quote(args.deployment_id, safe="")
        result = client.request("GET", path)
    elif args.deploy_command == "logs":
        deployment_id = urllib.parse.quote(args.deployment_id, safe="")
        result = client.request("GET", f"/api/workspaces/v1/deployments/{deployment_id}/logs")
    elif args.deploy_command == "activate":
        deployment_id = urllib.parse.quote(args.deployment_id, safe="")
        result = client.request("POST", f"/api/workspaces/v1/deployments/{deployment_id}/activate")
    else:
        deployment_id = urllib.parse.quote(args.deployment_id, safe="")
        result = client.request("POST", f"/api/workspaces/v1/deployments/{deployment_id}/accept")
    _show(result)


if __name__ == "__main__":
    main()
