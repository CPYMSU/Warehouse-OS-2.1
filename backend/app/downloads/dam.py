#!/usr/bin/env python3
"""dm.py 2.8.0 — Warehouse OS 智能數字資產託管客戶端。

這個版本只呼叫 Warehouse OS 2.1 原生端點：
  GET /api/workspaces/v1/info
  GET /api/workspaces/v1/usage
  GET /api/workspaces/v1/database/schema
  GET /api/workspaces/v1/data/{collection}
  PUT /api/workspaces/v1/data/{collection}/{record_key}
  POST /api/workspaces/v1/source-uploads
  PUT  /api/workspaces/v1/source-uploads/{id}/parts/{part_no}
  POST /api/workspaces/v1/source-uploads/{id}/complete
  GET  /api/workspaces/v1/source-uploads/{id}
  GET  /api/workspaces/v1/sources
  GET  /api/workspaces/v1/sources/{id}/download
  PUT  /api/workspaces/v1/runtime
  POST /api/workspaces/v1/storage/probe
  POST /api/workspaces/v1/deployments
  POST /api/workspaces/v1/jobs
  POST /api/workspaces/v1/releases/plan
  POST|GET /api/workspaces/v1/releases[/{id}]
  POST /api/workspaces/v1/releases/{id}/{resume|activate|cancel|rollback}
  GET|PUT /api/workspaces/v1/database/control|policy
  GET  /api/workspaces/v1/deployments[/{id}]
  GET  /api/hosting/v2/manifest
  GET  /api/hosting/v2/requirements
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
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "2.8.0"
DEFAULT_BASE = "__WAREHOUSE_BASE__"


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

    def wait_release(
        self,
        release_id: str,
        *,
        activate: bool,
        timeout_seconds: int,
    ) -> dict[str, object]:
        """Follow a server-owned release without making client uptime authoritative."""

        deadline = time.monotonic() + timeout_seconds
        passive = {
            "awaiting_activation",
            "verified",
            "failed",
            "rolled_back",
            "cancelled",
            "blocked",
        }
        observed: dict[str, object] = {}
        while time.monotonic() < deadline:
            reference = urllib.parse.quote(release_id, safe="")
            observed = self.request("GET", f"/api/workspaces/v1/releases/{reference}")
            release = observed.get("release") if isinstance(observed.get("release"), dict) else {}
            state = str(release.get("state") or "")
            if state in passive:
                if state == "awaiting_activation" and activate:
                    return self.request(
                        "POST",
                        f"/api/workspaces/v1/releases/{reference}/activate",
                    )
                return observed
            # This is an idempotent nudge. The Runtime Controller remains the
            # authority and continues after this CLI exits or loses connectivity.
            self.request("POST", f"/api/workspaces/v1/releases/{reference}/resume")
            time.sleep(2)
        raise SystemExit(
            f"發布 {release_id} 在 {timeout_seconds} 秒內未完成；"
            "服務端仍會繼續，可使用 release status 查看"
        )

    def upload_source(
        self,
        path: Path,
        *,
        version: str | None,
        component: str | None,
    ) -> dict[str, object]:
        if not path.is_file():
            raise SystemExit(f"找不到源碼壓縮包：{path}")
        digest = hashlib.sha256()
        size_bytes = 0
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size_bytes += len(chunk)
        sha256 = digest.hexdigest()
        upload = self.request(
            "POST",
            "/api/workspaces/v1/source-uploads",
            payload={
                "filename": path.name,
                "content_type": "application/octet-stream",
                "size_bytes": size_bytes,
                "sha256": sha256,
                "version_no": version,
                "component": component,
            },
            headers={"Idempotency-Key": f"source:{sha256}"},
        )
        upload_id = str(upload.get("upload_id") or "")
        if not upload_id:
            raise SystemExit("服務端沒有返回 upload_id")
        if upload.get("status") == "verified":
            return upload
        if upload.get("status") in {"failed", "expired", "cancelled"}:
            raise SystemExit(
                "源碼上傳無法恢復：" + json.dumps(upload.get("error") or upload, ensure_ascii=False)
            )
        chunk_size = int(upload.get("chunk_size_bytes") or 4 * 1024 * 1024)
        part_count = int(upload.get("part_count") or 0)
        received = {int(value) for value in (upload.get("received_parts") or [])}

        def put_part(part_no: int) -> dict[str, object]:
            with path.open("rb") as source:
                source.seek(part_no * chunk_size)
                content = source.read(chunk_size)
            part_digest = hashlib.sha256(content).hexdigest()
            request = urllib.request.Request(
                self.base + f"/api/workspaces/v1/source-uploads/{upload_id}/parts/{part_no}",
                data=content,
                method="PUT",
                headers={
                    "Authorization": "Bearer " + self.key,
                    "Accept": "application/json",
                    "Content-Type": "application/octet-stream",
                    "Content-SHA256": part_digest,
                    "User-Agent": f"WarehouseOS-dam/{VERSION}",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    value = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", "replace")
                raise RuntimeError(f"分片 {part_no} HTTP {exc.code}：{raw}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"分片 {part_no} 連接失敗：{exc.reason}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"分片 {part_no} 返回格式錯誤")
            return value

        missing = [part_no for part_no in range(part_count) if part_no not in received]
        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, min(4, len(missing)))
            ) as executor:
                futures = [executor.submit(put_part, part_no) for part_no in missing]
                for future in concurrent.futures.as_completed(futures):
                    future.result()
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        self.request(
            "POST",
            f"/api/workspaces/v1/source-uploads/{upload_id}/complete",
            payload={},
        )
        deadline = time.monotonic() + 15 * 60
        while time.monotonic() < deadline:
            observed = self.request("GET", f"/api/workspaces/v1/source-uploads/{upload_id}")
            state = str(observed.get("status") or "")
            if state == "verified":
                return observed
            if state in {"failed", "expired", "cancelled"}:
                raise SystemExit(
                    "源碼校驗失敗："
                    + json.dumps(observed.get("error") or observed, ensure_ascii=False)
                )
            time.sleep(0.5)
        raise SystemExit(f"源碼校驗仍在後台執行，可稍後查詢 upload_id={upload_id}")

    def upload_hosting_source(
        self,
        session_id: str,
        path: Path,
        *,
        version: str | None,
        component: str | None,
    ) -> dict[str, object]:
        uploaded = self.upload_source(path, version=version, component=component)
        source = uploaded.get("source") if isinstance(uploaded.get("source"), dict) else {}
        source_id = str(source.get("uuid") or uploaded.get("source_version_id") or "")
        if not source_id:
            raise SystemExit("已驗證上傳沒有返回 source_version_id")
        safe_session = urllib.parse.quote(session_id, safe="")
        return self.request(
            "POST",
            f"/api/hosting/v2/sessions/{safe_session}/sources/attach",
            payload={"source_version_id": source_id},
        )

    def download_source(self, source_id: str, output: Path | None) -> dict[str, object]:
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
                temporary = target.with_name(target.name + ".part")
                digest = hashlib.sha256()
                size = 0
                try:
                    with temporary.open("wb") as destination:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            destination.write(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                    expected = str(response.headers.get("Content-SHA256") or "").lower()
                    actual = digest.hexdigest()
                    if expected and expected != actual:
                        raise SystemExit(
                            f"下載 SHA-256 不一致：expected={expected} actual={actual}"
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


def _show(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _release_intent_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", dest="source_version_id")
    parser.add_argument("--component")
    parser.add_argument(
        "--type",
        dest="runtime_type",
        choices=("auto", "static", "web", "api", "worker", "agent", "container", "compose"),
        default="auto",
    )
    parser.add_argument("--runtime")
    parser.add_argument("--profile", dest="runtime_profile")
    parser.add_argument("--entrypoint")
    parser.add_argument("--build-command")
    parser.add_argument("--start-command")
    parser.add_argument("--health-path")


def _release_intent(args: argparse.Namespace) -> dict[str, object]:
    return {
        key: value
        for key, value in {
            "source_version_id": args.source_version_id,
            "component": args.component,
            "runtime_type": args.runtime_type,
            "runtime": args.runtime,
            "runtime_profile": args.runtime_profile,
            "entrypoint": args.entrypoint,
            "build_command": args.build_command,
            "start_command": args.start_command,
            "health_path": args.health_path,
        }.items()
        if value is not None
    }


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
        "--no-activate",
        dest="activate",
        action="store_false",
        default=True,
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

    project_commands = commands.add_parser("project", help="發布前專案診斷")
    project_subcommands = project_commands.add_subparsers(dest="project_command", required=True)
    project_doctor = project_subcommands.add_parser(
        "doctor", help="只讀檢查源碼、Runtime、資料庫任務、驗收與 Key 權限"
    )
    _release_intent_options(project_doctor)

    release_commands = commands.add_parser("release", help="執行可恢復的候選優先發布流程")
    release_subcommands = release_commands.add_subparsers(dest="release_command", required=True)
    release_plan = release_subcommands.add_parser("plan", help="產生不帶副作用的權威發布計畫")
    _release_intent_options(release_plan)
    release_run = release_subcommands.add_parser(
        "run", help="建立 Release 並等待候選任務與驗收完成"
    )
    _release_intent_options(release_run)
    release_run.add_argument("--idempotency-key", required=True)
    release_run.add_argument(
        "--activate",
        action="store_true",
        help="候選驗收成功後顯式切換流量並驗證公共路由",
    )
    release_run.add_argument(
        "--no-wait",
        action="store_true",
        help="建立後立即返回；服務端仍會繼續推進",
    )
    release_run.add_argument("--timeout", type=int, default=3600)
    release_status = release_subcommands.add_parser("status", help="查看 Release 狀態與事件")
    release_status.add_argument("release_id", nargs="?")
    for action, help_text in (
        ("resume", "冪等恢復一個中斷的 Release"),
        ("activate", "顯式激活已驗收的候選版本"),
        ("cancel", "取消尚未完成的 Release"),
        ("rollback", "切回 Release 建立時記錄的上一版本"),
    ):
        action_parser = release_subcommands.add_parser(action, help=help_text)
        action_parser.add_argument("release_id")

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
        "--no-activate",
        dest="activate",
        action="store_false",
        default=True,
        help="建立測試部署並保持目前 active 版本",
    )
    deploy_status = deploy_subcommands.add_parser("status", help="查看部署狀態")
    deploy_status.add_argument("deployment_id", nargs="?")
    deploy_logs = deploy_subcommands.add_parser("logs", help="查看部署事件與日誌")
    deploy_logs.add_argument("deployment_id")
    deploy_activate = deploy_subcommands.add_parser("activate", help="切換到既有 healthy 版本")
    deploy_activate.add_argument("deployment_id")
    deploy_accept = deploy_subcommands.add_parser("accept", help="依源碼契約私網驗收 staged 版本")
    deploy_accept.add_argument("deployment_id")

    job = commands.add_parser("job", help="執行不切換流量的受限一次性源碼任務")
    job.add_argument("--source", dest="source_version_id", required=True)
    job_selector = job.add_mutually_exclusive_group(required=True)
    job_selector.add_argument("--name", dest="job_name", help="manifest 聲明的 lifecycle job")
    job_selector.add_argument(
        "--command",
        dest="job_command",
        help="工作區邊界內的顯式一次性命令",
    )
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
        result = client.request("GET", "/api/hosting/v2/requirements")
    elif args.command == "project":
        result = client.request(
            "POST",
            "/api/workspaces/v1/releases/plan",
            payload=_release_intent(args),
        )
    elif args.command == "release":
        if args.release_command == "plan":
            result = client.request(
                "POST",
                "/api/workspaces/v1/releases/plan",
                payload=_release_intent(args),
            )
        elif args.release_command == "run":
            if args.no_wait and args.activate:
                raise SystemExit("--activate 不能與 --no-wait 同時使用")
            result = client.request(
                "POST",
                "/api/workspaces/v1/releases",
                payload=_release_intent(args),
                headers={"Idempotency-Key": args.idempotency_key},
            )
            release = result.get("release") if isinstance(result.get("release"), dict) else {}
            release_id = str(release.get("uuid") or release.get("id") or "")
            if not release_id:
                raise SystemExit("服務端沒有返回 release id")
            if not args.no_wait:
                result = client.wait_release(
                    release_id,
                    activate=args.activate,
                    timeout_seconds=max(30, args.timeout),
                )
        elif args.release_command == "status":
            path = "/api/workspaces/v1/releases"
            if args.release_id:
                path += "/" + urllib.parse.quote(args.release_id, safe="")
            result = client.request("GET", path)
        else:
            release_id = urllib.parse.quote(args.release_id, safe="")
            result = client.request(
                "POST",
                f"/api/workspaces/v1/releases/{release_id}/{args.release_command}",
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
                "command": args.job_command,
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
            headers=({"Idempotency-Key": args.idempotency_key} if args.idempotency_key else None),
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
