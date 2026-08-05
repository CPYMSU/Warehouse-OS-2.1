#!/usr/bin/env python3
"""Root-owned, fixed-capability host agent for the Warehouse SHIELD control plane.

The API receives only an authenticated Unix socket.  It never receives the
Docker socket, a host shell, or a user-controlled command surface.
"""

from __future__ import annotations

import hmac
import json
import os
import platform
import re
import shutil
import socketserver
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

IS_DARWIN = platform.system() == "Darwin"
MAC_DEPLOY_ROOT = Path(
    os.environ.get("WAREHOUSE_MAC_DEPLOY_ROOT", str(Path.home() / "Server/bonfirework"))
)
ENV_FILE = Path(
    os.environ.get(
        "WAREHOUSE_SHIELD_ENV_FILE",
        str(MAC_DEPLOY_ROOT / "shared/orbstack.env") if IS_DARWIN else "/etc/warehouse-os/runtime.env",
    )
)


def configured_value(key: str, default: str = "") -> str:
    supplied = os.environ.get(key)
    if supplied is not None:
        return supplied
    try:
        lines = ENV_FILE.read_text(encoding="utf-8", errors="strict").splitlines()
    except OSError:
        return default
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        if separator and name.strip() == key:
            clean = value.strip()
            if len(clean) >= 2 and clean[0] == clean[-1] and clean[0] in {"'", '"'}:
                clean = clean[1:-1]
            return clean
    return default


SOCKET_PATH = Path(
    configured_value(
        "WAREHOUSE_SHIELD_AGENT_SOCKET",
        str(MAC_DEPLOY_ROOT / "shared/shield/agent.sock")
        if IS_DARWIN
        else "/run/warehouse-shield/agent.sock",
    )
)
TCP_HOST = configured_value(
    "WAREHOUSE_SHIELD_AGENT_TCP_HOST", "127.0.0.1" if IS_DARWIN else ""
)
TCP_PORT = int(
    configured_value("WAREHOUSE_SHIELD_AGENT_TCP_PORT", "18091" if IS_DARWIN else "0")
)
TOKEN = configured_value("WAREHOUSE_SHIELD_AGENT_TOKEN")
APPLY_ENABLED = configured_value("WAREHOUSE_SHIELD_REPAIR_APPLY", "false").lower() in {
    "1", "true", "yes", "on"
}
DEPLOY_STATE = Path(
    configured_value(
        "WAREHOUSE_SHIELD_DEPLOY_STATE",
        str(MAC_DEPLOY_ROOT / "state") if IS_DARWIN else "/opt/warehouse-os/shared/deploy-state",
    )
)
HEALTH_FLAG = Path(
    configured_value(
        "WAREHOUSE_SHIELD_HEALTH_FLAG",
        str(MAC_DEPLOY_ROOT / "shared/shield/health_fail")
        if IS_DARWIN
        else "/opt/warehouse-os/shared/shield/health_fail",
    )
)
AGENT_LOG = Path(
    configured_value(
        "WAREHOUSE_SHIELD_AGENT_LOG",
        str(MAC_DEPLOY_ROOT / "shared/logs/warehouse-shield.jsonl")
        if IS_DARWIN
        else "/var/log/warehouse-shield.jsonl",
    )
)
NGINX_ACCESS_LOG = Path(configured_value("WAREHOUSE_SHIELD_ACCESS_LOG", "/var/log/nginx/access.log"))
NGINX_DOMAIN_AVAILABLE = Path("/etc/nginx/sites-available")
NGINX_DOMAIN_ENABLED = Path("/etc/nginx/sites-enabled")
BACKUP_DIR = Path(
    configured_value(
        "WAREHOUSE_SHIELD_BACKUP_DIR",
        str(MAC_DEPLOY_ROOT / "shared/backups") if IS_DARWIN else "/opt/warehouse-os/backups",
    )
)
if IS_DARWIN:
    # The shared environment also serves Linux containers and therefore keeps
    # /mnt/warehouse-data and /dev/vdb1 values.  Those must never override the
    # Mac host probe: OrbStack data is hosted by the Mac filesystem instead.
    DATA_MOUNTPOINT = Path(
        configured_value(
            "WAREHOUSE_SHIELD_MAC_DATA_MOUNTPOINT",
            str(Path.home() / "Server/bonfirework-migration"),
        )
    )
    DATA_DEVICE = configured_value("WAREHOUSE_SHIELD_MAC_DATA_DEVICE", "")
    DATA_VOLUME_REQUIRED = configured_value(
        "WAREHOUSE_SHIELD_MAC_DATA_VOLUME_REQUIRED", "false"
    ).lower() in {"1", "true", "yes", "on"}
else:
    DATA_MOUNTPOINT = Path(
        configured_value("WAREHOUSE_SHIELD_DATA_MOUNTPOINT", "/mnt/warehouse-data")
    )
    DATA_DEVICE = configured_value("WAREHOUSE_SHIELD_DATA_DEVICE", "/dev/vdb1")
    DATA_VOLUME_REQUIRED = configured_value(
        "WAREHOUSE_SHIELD_DATA_VOLUME_REQUIRED", "false"
    ).lower() in {"1", "true", "yes", "on"}
API_PORT = int(configured_value("WAREHOUSE_SHIELD_API_PORT", "8081" if IS_DARWIN else "0"))
DOCKER_BIN = configured_value(
    "WAREHOUSE_DOCKER_BIN",
    str(Path.home() / ".orbstack/bin/docker") if IS_DARWIN else "docker",
)
MAX_REQUEST_BYTES = 64 * 1024
ALLOWED_ACTIONS = {
    "healthcheck",
    "restart-api",
    "restart-firefighter",
    "reload-nginx",
    "restart-nginx",
    "clear-health-flag",
}
HOSTNAME_RE = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")

_sample_lock = threading.Lock()
_previous_cpu: tuple[int, int] | None = None
_previous_net: tuple[float, int, int] | None = None
_previous_process: dict[int, tuple[float, int]] = {}
_status_cache_lock = threading.Lock()
_status_cache: tuple[float, dict[str, object]] | None = None


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def log_event(event: str, **payload: object) -> None:
    row = {"time": now_iso(), "event": event, **payload}
    AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AGENT_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def run_fixed(arguments: list[str], timeout: float = 15.0) -> dict[str, object]:
    try:
        completed = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                "PATH": (
                    f"{Path.home()}/.orbstack/bin:/opt/homebrew/bin:"
                    "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
                )
            },
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:].strip(),
            "stderr": completed.stderr[-4000:].strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": 124, "stdout": "", "stderr": type(exc).__name__}


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return default


def active_slot() -> str:
    if IS_DARWIN:
        return "mac"
    slot = read_text(DEPLOY_STATE / "active-slot").strip()
    return slot if slot in {"blue", "green"} else ""


def active_port() -> int:
    if API_PORT > 0:
        return API_PORT
    return 18081 if active_slot() == "blue" else 18082 if active_slot() == "green" else 8080


def active_container() -> str:
    if IS_DARWIN:
        return "bonfirework-mac-api"
    slot = active_slot()
    return f"warehouse-os-api-{slot}" if slot else "warehouse-os-api-1"


def http_probe(path: str = "/api/health", timeout: float = 4.0) -> dict[str, object]:
    url = f"http://127.0.0.1:{active_port()}{path}"
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(65536)
            parsed = json.loads(body) if body else {}
            return {
                "ok": 200 <= response.status < 300,
                "http_status": response.status,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "body": parsed if isinstance(parsed, dict) else {},
            }
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "http_status": getattr(exc, "code", None),
            "latency_ms": round((time.monotonic() - started) * 1000),
            "error": type(exc).__name__,
        }


def service_active(unit: str) -> bool:
    if IS_DARWIN:
        if unit == "warehouse-shield-agent":
            return True
        process_names = {
            "nginx": ("nginx", "caddy", "cloudflared"),
        }.get(unit, (unit,))
        return any(run_fixed(["pgrep", "-x", name], timeout=4)["returncode"] == 0 for name in process_names)
    result = run_fixed(["systemctl", "is-active", "--quiet", unit], timeout=4)
    return result["returncode"] == 0


def container_state(name: str) -> dict[str, object]:
    result = run_fixed(
        [DOCKER_BIN, "inspect", "--format", "{{.State.Status}}|{{.State.Health.Status}}|{{.State.Pid}}", name],
        timeout=5,
    )
    if result["returncode"] != 0:
        return {"state": "offline", "pid": None}
    parts = str(result["stdout"]).strip().split("|")
    status = parts[0] if parts else ""
    health = parts[1] if len(parts) > 1 and parts[1] != "<no value>" else ""
    pid = parts[2] if len(parts) > 2 else ""
    return {
        "state": "online" if status == "running" and health in {"", "healthy"} else "degraded",
        "container_status": status,
        "health": health or None,
        "pid": int(pid) if pid.strip().isdigit() else None,
    }


def cpu_sample() -> dict[str, object]:
    global _previous_cpu
    if IS_DARWIN:
        result = run_fixed(["ps", "-A", "-o", "%cpu="], timeout=5)
        values: list[float] = []
        if result["returncode"] == 0:
            for value in str(result["stdout"]).split():
                try:
                    values.append(float(value))
                except ValueError:
                    continue
        loads = os.getloadavg()
        cores = os.cpu_count() or 1
        return {
            "usage_pct": round(min(100.0, sum(values) / cores), 2) if values else None,
            "load_1m": round(loads[0], 3),
            "load_5m": round(loads[1], 3),
            "load_15m": round(loads[2], 3),
            "load_normalized_pct": round(loads[0] / cores * 100, 2),
            "logical_cores": cores,
        }
    fields = read_text(Path("/proc/stat")).splitlines()[0].split()
    values = [int(value) for value in fields[1:]] if fields and fields[0] == "cpu" else []
    total = sum(values)
    idle = sum(values[index] for index in (3, 4) if index < len(values))
    usage: float | None = None
    with _sample_lock:
        if _previous_cpu and total > _previous_cpu[0]:
            total_delta = total - _previous_cpu[0]
            idle_delta = idle - _previous_cpu[1]
            usage = round(100 * (1 - idle_delta / total_delta), 2)
        _previous_cpu = (total, idle)
    loads = os.getloadavg()
    cores = os.cpu_count() or 1
    return {
        "usage_pct": usage,
        "load_1m": round(loads[0], 3),
        "load_5m": round(loads[1], 3),
        "load_15m": round(loads[2], 3),
        "load_normalized_pct": round(loads[0] / cores * 100, 2),
        "logical_cores": cores,
    }


def memory_sample() -> dict[str, object]:
    if IS_DARWIN:
        total_result = run_fixed(["sysctl", "-n", "hw.memsize"], timeout=4)
        total = int(str(total_result["stdout"]).strip() or 0) if total_result["returncode"] == 0 else 0
        vm_result = run_fixed(["vm_stat"], timeout=4)
        page_size = 4096
        counters: dict[str, int] = {}
        for line in str(vm_result["stdout"]).splitlines():
            page_match = re.search(r"page size of (\d+) bytes", line)
            if page_match:
                page_size = int(page_match.group(1))
            key, separator, raw = line.partition(":")
            if separator:
                digits = re.sub(r"[^0-9]", "", raw)
                if digits:
                    counters[key.strip()] = int(digits)
        available_pages = sum(
            counters.get(key, 0)
            for key in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable")
        )
        available = min(total, available_pages * page_size) if total else 0
        swap_result = run_fixed(["sysctl", "-n", "vm.swapusage"], timeout=4)
        swap_match = re.search(r"used = ([0-9.]+)([MG])", str(swap_result["stdout"]))
        swap_used = 0
        if swap_match:
            factor = 1024**3 if swap_match.group(2) == "G" else 1024**2
            swap_used = round(float(swap_match.group(1)) * factor)
        return {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": max(0, total - available),
            "used_pct": round((total - available) / total * 100, 2) if total else None,
            "swap_used_bytes": swap_used,
            "swap_used_pct": None,
        }
    values: dict[str, int] = {}
    for line in read_text(Path("/proc/meminfo")).splitlines():
        match = re.match(r"^(\w+):\s+(\d+)", line)
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    swap_total = values.get("SwapTotal", 0)
    swap_used = max(0, swap_total - values.get("SwapFree", 0))
    return {
        "total_bytes": total,
        "available_bytes": available,
        "used_bytes": max(0, total - available),
        "used_pct": round((total - available) / total * 100, 2) if total else None,
        "swap_used_bytes": swap_used,
        "swap_used_pct": round(swap_used / swap_total * 100, 2) if swap_total else 0,
    }


def mount_metadata(mountpoint: Path) -> dict[str, object]:
    if IS_DARWIN:
        result = run_fixed(["df", "-k", str(mountpoint)], timeout=4)
        lines = str(result["stdout"]).splitlines()
        if result["returncode"] != 0 or len(lines) < 2:
            return {}
        fields = lines[-1].split()
        return {
            "source": fields[0] if fields else None,
            "target": fields[-1] if fields else str(mountpoint),
            "fstype": None,
        }
    result = run_fixed(
        [
            "findmnt",
            "--json",
            "--output",
            "SOURCE,TARGET,FSTYPE,UUID,LABEL,OPTIONS",
            "--target",
            str(mountpoint),
        ],
        timeout=4,
    )
    if result["returncode"] != 0:
        return {}
    try:
        payload = json.loads(str(result["stdout"]))
    except json.JSONDecodeError:
        return {}
    filesystems = payload.get("filesystems") if isinstance(payload, dict) else None
    if not isinstance(filesystems, list) or not filesystems or not isinstance(filesystems[0], dict):
        return {}
    return {
        str(key): value
        for key, value in filesystems[0].items()
        if value not in (None, "")
    }


def volume_sample(
    *,
    volume_id: str,
    label: str,
    mountpoint: Path,
    expected_device: str | None = None,
    required: bool = True,
) -> dict[str, object]:
    mounted = os.path.ismount(mountpoint) or (IS_DARWIN and mountpoint.is_dir())
    device_present = Path(expected_device).exists() if expected_device else None
    metadata = mount_metadata(mountpoint) if mounted else {}
    source = str(metadata.get("source") or "") or None
    device_matches: bool | None = None
    if expected_device and source:
        device_matches = os.path.realpath(source) == os.path.realpath(expected_device)
    base: dict[str, object] = {
        "id": volume_id,
        "label": label,
        "mountpoint": str(mountpoint),
        "expected_device": expected_device,
        "device": source or expected_device,
        "device_present": device_present,
        "device_matches": device_matches,
        "filesystem": metadata.get("fstype"),
        "filesystem_label": metadata.get("label"),
        "uuid": metadata.get("uuid"),
        "options": metadata.get("options"),
        "mounted": mounted,
        "required": required,
        "available": False,
        "state": "missing" if expected_device and device_present is False else "unmounted",
        "total_bytes": None,
        "used_bytes": None,
        "free_bytes": None,
        "used_pct": None,
    }
    if not mounted:
        return base
    try:
        disk = shutil.disk_usage(mountpoint)
    except OSError:
        base["state"] = "unavailable"
        return base
    base.update(
        {
            "available": True,
            "state": "unexpected-device" if device_matches is False else "mounted",
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "used_pct": round(disk.used / disk.total * 100, 2) if disk.total else None,
        }
    )
    return base


def storage_sample() -> dict[str, object]:
    root = volume_sample(
        volume_id="root",
        label="Root volume",
        mountpoint=Path("/"),
    )
    data = volume_sample(
        volume_id="warehouse-data",
        label="Warehouse data",
        mountpoint=DATA_MOUNTPOINT,
        expected_device=DATA_DEVICE,
        required=DATA_VOLUME_REQUIRED,
    )
    return {
        # Preserve the v1 root-volume fields for stored snapshots and older clients.
        "total_bytes": root["total_bytes"],
        "used_bytes": root["used_bytes"],
        "free_bytes": root["free_bytes"],
        "used_pct": root["used_pct"],
        "volumes": [root, data],
    }


def storage_alerts(storage: dict[str, object]) -> list[dict[str, object]]:
    alerts: list[dict[str, object]] = []
    root_pct = storage.get("used_pct")
    if isinstance(root_pct, (int, float)) and float(root_pct) >= 90:
        alerts.append(
            {
                "code": "storage-pressure",
                "label": "Root volume pressure",
                "severity": 4,
                "value": root_pct,
                "unit": "%",
            }
        )
    volumes = storage.get("volumes")
    if not isinstance(volumes, list):
        return alerts
    data = next(
        (
            item
            for item in volumes
            if isinstance(item, dict) and item.get("id") == "warehouse-data"
        ),
        None,
    )
    if not isinstance(data, dict) or data.get("required") is not True:
        return alerts
    state = str(data.get("state") or "unknown")
    if data.get("mounted") is not True:
        alerts.append(
            {
                "code": "data-volume-unmounted",
                "label": "Warehouse data volume is not mounted",
                "severity": 4,
                "value": state,
                "unit": "",
            }
        )
    elif state == "unexpected-device":
        alerts.append(
            {
                "code": "data-volume-device-mismatch",
                "label": "Warehouse data mount uses an unexpected device",
                "severity": 5,
                "value": data.get("device"),
                "unit": "",
            }
        )
    elif data.get("available") is not True:
        alerts.append(
            {
                "code": "data-volume-unavailable",
                "label": "Warehouse data volume metrics are unavailable",
                "severity": 4,
                "value": state,
                "unit": "",
            }
        )
    elif isinstance(data.get("used_pct"), (int, float)) and float(data["used_pct"]) >= 90:
        alerts.append(
            {
                "code": "data-volume-pressure",
                "label": "Warehouse data volume pressure",
                "severity": 4,
                "value": data["used_pct"],
                "unit": "%",
            }
        )
    return alerts


def network_sample() -> dict[str, object]:
    global _previous_net
    rx = tx = 0
    if IS_DARWIN:
        result = run_fixed(["netstat", "-ibn"], timeout=5)
        lines = str(result["stdout"]).splitlines()
        header = next((line.split() for line in lines if "Ibytes" in line and "Obytes" in line), [])
        ibytes = header.index("Ibytes") if "Ibytes" in header else -1
        obytes = header.index("Obytes") if "Obytes" in header else -1
        seen: set[str] = set()
        for line in lines:
            fields = line.split()
            if not fields or fields[0] == "Name" or fields[0].startswith("lo"):
                continue
            if fields[0] in seen or max(ibytes, obytes) >= len(fields):
                continue
            if ibytes >= 0 and obytes >= 0 and fields[ibytes].isdigit() and fields[obytes].isdigit():
                seen.add(fields[0])
                rx += int(fields[ibytes])
                tx += int(fields[obytes])
    else:
        for line in read_text(Path("/proc/net/dev")).splitlines()[2:]:
            if ":" not in line:
                continue
            interface, counters = line.split(":", 1)
            if interface.strip() == "lo":
                continue
            values = counters.split()
            if len(values) >= 9:
                rx += int(values[0])
                tx += int(values[8])
    sampled = time.monotonic()
    rx_rate = tx_rate = None
    with _sample_lock:
        if _previous_net and sampled > _previous_net[0]:
            elapsed = sampled - _previous_net[0]
            rx_rate = round(max(0, rx - _previous_net[1]) / elapsed, 2)
            tx_rate = round(max(0, tx - _previous_net[2]) / elapsed, 2)
        _previous_net = (sampled, rx, tx)
    established = listening = 0
    if IS_DARWIN:
        sockets = run_fixed(["netstat", "-an", "-p", "tcp"], timeout=5)
        for line in str(sockets["stdout"]).splitlines():
            established += "ESTABLISHED" in line
            listening += "LISTEN" in line
    else:
        for table in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
            for line in read_text(table).splitlines()[1:]:
                parts = line.split()
                if len(parts) > 3:
                    established += parts[3] == "01"
                    listening += parts[3] == "0A"
    return {
        "rx_bytes": rx,
        "tx_bytes": tx,
        "rx_bytes_per_second": rx_rate,
        "tx_bytes_per_second": tx_rate,
        "established_tcp": established,
        "listening_tcp": listening,
    }


def process_sample(pid: int | None) -> dict[str, object]:
    if IS_DARWIN:
        result = run_fixed(
            [
                DOCKER_BIN, "stats", "--no-stream", "--format",
                "{{.CPUPerc}}|{{.MemUsage}}|{{.PIDs}}", active_container(),
            ],
            timeout=8,
        )
        if result["returncode"] != 0:
            return {}
        values = str(result["stdout"]).strip().split("|", 2)
        cpu_text = values[0].strip().rstrip("%") if values else ""
        memory_text = values[1].split("/", 1)[0].strip() if len(values) > 1 else ""
        memory_match = re.fullmatch(r"([0-9.]+)([KMG]i?B)", memory_text)
        factors = {"KB": 1000, "KiB": 1024, "MB": 1000**2, "MiB": 1024**2, "GB": 1000**3, "GiB": 1024**3}
        rss_bytes = (
            round(float(memory_match.group(1)) * factors[memory_match.group(2)])
            if memory_match
            else None
        )
        return {
            "pid": pid,
            "cpu_pct": float(cpu_text) if cpu_text else None,
            "rss_bytes": rss_bytes,
            "threads": int(values[2]) if len(values) > 2 and values[2].strip().isdigit() else None,
            "fd_open": None,
            "fd_limit": None,
            "uptime_seconds": None,
        }
    if not pid:
        return {}
    status: dict[str, str] = {}
    for line in read_text(Path(f"/proc/{pid}/status")).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            status[key] = value.strip()
    stat = read_text(Path(f"/proc/{pid}/stat")).split()
    ticks = int(stat[13]) + int(stat[14]) if len(stat) > 21 else 0
    started_ticks = int(stat[21]) if len(stat) > 21 else 0
    uptime = float(read_text(Path("/proc/uptime"), "0").split()[0])
    hertz = os.sysconf("SC_CLK_TCK")
    sampled = time.monotonic()
    cpu_pct: float | None = None
    with _sample_lock:
        previous = _previous_process.get(pid)
        if previous and sampled > previous[0]:
            cpu_pct = round((ticks - previous[1]) / hertz / (sampled - previous[0]) * 100, 2)
        _previous_process[pid] = (sampled, ticks)
    fd_path = Path(f"/proc/{pid}/fd")
    try:
        fd_open = len(list(fd_path.iterdir()))
    except OSError:
        fd_open = None
    limits = read_text(Path(f"/proc/{pid}/limits"))
    fd_match = re.search(r"^Max open files\s+(\d+)\s+(\d+)", limits, re.MULTILINE)
    return {
        "pid": pid,
        "cpu_pct": cpu_pct,
        "rss_bytes": int(status.get("VmRSS", "0 kB").split()[0]) * 1024,
        "threads": int(status.get("Threads", "0")),
        "fd_open": fd_open,
        "fd_limit": int(fd_match.group(1)) if fd_match else None,
        "uptime_seconds": max(0, round(uptime - started_ticks / hertz)),
    }


def nginx_traffic() -> dict[str, object]:
    cutoff = datetime.now(UTC) - timedelta(minutes=2)
    requests = failures = login_failures = 0
    lines = read_text(NGINX_ACCESS_LOG).splitlines()[-4000:]
    pattern = re.compile(r"\[([^]]+)\].*\"(?:GET|POST|PUT|PATCH|DELETE|OPTIONS) ([^ ]+).*\" (\d{3}) ")
    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        try:
            observed = datetime.strptime(match.group(1), "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            continue
        if observed < cutoff:
            continue
        requests += 1
        status = int(match.group(3))
        failures += status >= 500
        login_failures += "/api/auth/login" in match.group(2) and status == 401
    return {
        "requests_per_second": round(requests / 120, 3),
        "errors_5xx_pct": round(failures / requests * 100, 3) if requests else 0,
        "login_failures": login_failures,
    }


def ssh_failures() -> int | None:
    if IS_DARWIN:
        return None
    result = run_fixed(
        ["journalctl", "-u", "ssh", "-u", "sshd", "--since", "2 minutes ago", "--no-pager", "-q"],
        timeout=5,
    )
    if result["returncode"] not in {0, 1}:
        return None
    return sum(
        "failed password" in line.lower() or "authentication failure" in line.lower()
        for line in str(result["stdout"]).splitlines()
    )


def tail_guardian(limit: int = 80) -> list[str]:
    return read_text(AGENT_LOG).splitlines()[-limit:]


def host_uptime_seconds() -> int:
    if not IS_DARWIN:
        return round(float(read_text(Path("/proc/uptime"), "0").split()[0]))
    result = run_fixed(["sysctl", "-n", "kern.boottime"], timeout=4)
    match = re.search(r"sec\s*=\s*(\d+)", str(result["stdout"]))
    return max(0, round(time.time() - int(match.group(1)))) if match else 0


def collect_status() -> dict[str, object]:
    api_container = container_state(active_container())
    probe = http_probe()
    cpu = cpu_sample()
    memory = memory_sample()
    storage = storage_sample()
    network = network_sample()
    traffic = nginx_traffic()
    traffic["api_health_latency_ms"] = probe.get("latency_ms")
    process = process_sample(api_container.get("pid") if isinstance(api_container.get("pid"), int) else None)
    integrity_mismatch = 1 if HEALTH_FLAG.exists() else 0
    ssh_failure_count = ssh_failures()
    alerts: list[dict[str, object]] = []

    def alert(code: str, label: str, severity: int, value: object = None, unit: str = "") -> None:
        alerts.append({"code": code, "label": label, "severity": severity, "value": value, "unit": unit})

    if not probe.get("ok"):
        alert("api-health-failed", "Warehouse API health probe failed", 5, probe.get("http_status"))
    if isinstance(cpu.get("usage_pct"), (int, float)) and float(cpu["usage_pct"]) >= 90:
        alert("cpu-pressure", "CPU pressure", 3, cpu["usage_pct"], "%")
    if isinstance(memory.get("used_pct"), (int, float)) and float(memory["used_pct"]) >= 90:
        alert("memory-pressure", "Memory pressure", 4, memory["used_pct"], "%")
    alerts.extend(storage_alerts(storage))
    if integrity_mismatch:
        alert("integrity-drift", "Integrity health flag is present", 5, integrity_mismatch)
    severity = max((int(item["severity"]) for item in alerts), default=0)
    state = "healthy"
    if integrity_mismatch:
        state = "integrity-alert"
    elif severity >= 5:
        state = "incident"
    elif severity >= 3:
        state = "degraded"
    elif alerts:
        state = "watch"
    services = [
        {"id": "warehouse-api", "state": api_container.get("state", "unknown")},
        {"id": "nginx", "state": "online" if service_active("nginx") else "offline"},
        {"id": "firefighter", "state": "online" if service_active("warehouse-shield-agent") else "offline"},
        {"id": "guardian", "state": "alert" if integrity_mismatch else "online"},
        {"id": "database", "state": "online" if probe.get("ok") else "unknown"},
        {"id": "ai-engine", "state": "unknown"},
    ]
    uptime = host_uptime_seconds()
    backups = [path for path in BACKUP_DIR.glob("*") if path.is_file()]
    vitals = {
        "schema_version": 2,
        "sampled_at": now_iso(),
        "poll_hint_seconds": 5,
        "state": state,
        "severity": severity,
        "health_score": max(0, 100 - severity * 18 - min(10, len(alerts) * 2)),
        "cpu": cpu,
        "memory": memory,
        "storage": storage,
        "network": network,
        "process": process,
        "runtime": {
            "uptime_seconds": uptime,
            "platform": platform.system(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
        },
        "thermal": {"available": False, "temperature_c": None},
        "traffic": traffic,
        "security": {
            "login_failures": traffic["login_failures"],
            "ssh_failures": ssh_failure_count,
            "new_listener_signal": 0,
            "integrity_mismatch": integrity_mismatch,
        },
        "resilience": {
            "backup_count": len(backups),
            "disk_growth_gb_per_day": None,
            "swap_used_mb_observed": round(int(memory.get("swap_used_bytes") or 0) / 1024 / 1024, 1),
        },
        "services": services,
        "data_sources": {
            "kernel": {"state": "online"},
            "storage": {
                "state": "alert"
                if any(
                    item.get("code", "").startswith(("storage-", "data-volume-"))
                    for item in alerts
                )
                else "online",
                "volumes": len(storage.get("volumes", [])),
            },
            "firefighter": {"state": "online" if service_active("warehouse-shield-agent") else "offline"},
            "guardian": {"state": "alert" if integrity_mismatch else "online"},
        },
        "alerts": alerts,
    }
    return {"ok": True, "system_vitals": vitals, "guardian_tail": tail_guardian()}


def cached_status() -> dict[str, object]:
    global _status_cache
    with _status_cache_lock:
        sampled = time.monotonic()
        if _status_cache and sampled - _status_cache[0] < 3:
            return _status_cache[1]
        response = collect_status()
        _status_cache = (sampled, response)
        return response


def schedule_fixed(arguments: list[str], label: str) -> None:
    def execute() -> None:
        result = run_fixed(arguments, timeout=90)
        log_event("scheduled-action-complete", action=label, **result)

    timer = threading.Timer(2.0, execute)
    timer.daemon = True
    timer.start()


def execute_action(action: str, apply: bool, request_id: str) -> dict[str, object]:
    if action not in ALLOWED_ACTIONS:
        return {"ok": False, "status": "failed", "applied": False, "error": "action_not_allowed"}
    if action == "healthcheck":
        probe = http_probe()
        result = {
            "status": "healthy" if probe.get("ok") else "unhealthy",
            **probe,
            "active_slot": active_slot() or "legacy",
            "container": active_container(),
        }
        log_event("healthcheck", request_id=request_id, ok=bool(probe.get("ok")))
        return {"ok": bool(probe.get("ok")), "status": "succeeded" if probe.get("ok") else "failed", "applied": False, "result": result}
    if not apply or not APPLY_ENABLED:
        log_event("repair-dry-run", request_id=request_id, action=action)
        return {
            "ok": True,
            "status": "succeeded",
            "applied": False,
            "result": {"status": "dry-run", "action": action, "apply_enabled": APPLY_ENABLED},
        }
    if action in {"reload-nginx", "restart-nginx"}:
        if IS_DARWIN:
            return {
                "ok": False,
                "status": "blocked",
                "applied": False,
                "error": "mac_edge_proxy_is_managed_by_the_cluster_gateway",
            }
        validation = run_fixed(["nginx", "-t"], timeout=15)
        if validation["returncode"] != 0:
            return {"ok": False, "status": "failed", "applied": False, "error": "nginx_config_invalid", "result": validation}
        operation = "reload" if action == "reload-nginx" else "restart"
        result = run_fixed(["systemctl", operation, "nginx"], timeout=30)
        ok = result["returncode"] == 0
        log_event("repair-complete", request_id=request_id, action=action, ok=ok)
        return {"ok": ok, "status": "succeeded" if ok else "failed", "applied": ok, "returncode": result["returncode"], "result": result}
    if action == "clear-health-flag":
        existed = HEALTH_FLAG.exists()
        try:
            HEALTH_FLAG.unlink(missing_ok=True)
            ok = True
            error = None
        except OSError as exc:
            ok = False
            error = type(exc).__name__
        log_event("repair-complete", request_id=request_id, action=action, ok=ok)
        return {"ok": ok, "status": "succeeded" if ok else "failed", "applied": ok, "result": {"removed": existed}, "error": error}
    if action == "restart-api":
        container = active_container()
        schedule_fixed([DOCKER_BIN, "restart", container], action)
        log_event("repair-scheduled", request_id=request_id, action=action, target=container)
        return {"ok": True, "status": "scheduled", "applied": True, "result": {"target": container, "delay_seconds": 2}}
    if IS_DARWIN:
        target = f"gui/{os.getuid()}/org.bonfirework.warehouse-shield-agent"
        schedule_fixed(["launchctl", "kickstart", "-k", target], action)
        log_event("repair-scheduled", request_id=request_id, action=action, target=target)
        return {"ok": True, "status": "scheduled", "applied": True, "result": {"target": target, "delay_seconds": 2}}
    schedule_fixed(["systemctl", "restart", "warehouse-shield-agent"], action)
    log_event("repair-scheduled", request_id=request_id, action=action)
    return {"ok": True, "status": "scheduled", "applied": True, "result": {"target": "warehouse-shield-agent", "delay_seconds": 2}}


def apply_hosting_domain(payload: dict[str, Any], request_id: str) -> dict[str, object]:
    if IS_DARWIN:
        return {
            "ok": False,
            "status": "blocked",
            "applied": False,
            "error": "mac_hosting_domains_are_managed_by_the_cluster_gateway",
        }
    hostname = str(payload.get("hostname") or "").strip().lower().rstrip(".")
    tenant_slug = str(payload.get("tenant_slug") or "").strip().lower()
    workspace_key = str(payload.get("workspace_key") or "").strip().lower()
    if (
        not HOSTNAME_RE.fullmatch(hostname)
        or not SLUG_RE.fullmatch(tenant_slug)
        or not SLUG_RE.fullmatch(workspace_key)
    ):
        return {
            "ok": False,
            "status": "failed",
            "error": "invalid_hosting_domain_contract",
        }
    filename = f"warehouse-hosting-{hostname}.conf"
    available = NGINX_DOMAIN_AVAILABLE / filename
    enabled = NGINX_DOMAIN_ENABLED / filename
    try:
        for candidate in NGINX_DOMAIN_ENABLED.iterdir():
            if candidate == enabled:
                continue
            contents = candidate.read_text(encoding="utf-8", errors="replace")
            server_names = re.findall(r"\bserver_name\s+([^;]+);", contents)
            if any(hostname in names.split() for names in server_names):
                return {
                    "ok": False,
                    "status": "blocked",
                    "error": "hostname_already_configured_on_host",
                }
    except OSError as exc:
        return {
            "ok": False,
            "status": "failed",
            "error": f"nginx_domain_inventory_failed:{type(exc).__name__}",
        }
    configuration = f"""server {{
    listen 80;
    listen [::]:80;
    server_name {hostname};
    client_max_body_size 260m;
    location / {{
        rewrite ^/(.*)$ /assets/{tenant_slug}/{workspace_key}/$1 break;
        include /etc/nginx/snippets/warehouse-api-upstream.conf;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }}
}}
"""
    temporary = available.with_suffix(".tmp")
    try:
        temporary.write_text(configuration, encoding="utf-8")
        temporary.chmod(0o640)
        temporary.replace(available)
        enabled.unlink(missing_ok=True)
        enabled.symlink_to(available)
    except OSError as exc:
        return {
            "ok": False,
            "status": "failed",
            "error": f"nginx_domain_write_failed:{type(exc).__name__}",
        }
    validation = run_fixed(["nginx", "-t"], timeout=20)
    if validation["returncode"] != 0:
        enabled.unlink(missing_ok=True)
        available.unlink(missing_ok=True)
        return {
            "ok": False,
            "status": "failed",
            "error": "nginx_config_invalid",
            "result": validation,
        }
    reload_result = run_fixed(["systemctl", "reload", "nginx"], timeout=30)
    if reload_result["returncode"] != 0:
        return {
            "ok": False,
            "status": "failed",
            "error": "nginx_reload_failed",
            "result": reload_result,
        }
    if shutil.which("certbot") is None:
        return {
            "ok": False,
            "status": "blocked",
            "error": "acme_client_unavailable",
            "result": {"http_route_configured": True, "hostname": hostname},
        }
    certificate = run_fixed(
        [
            "certbot",
            "--nginx",
            "--non-interactive",
            "--agree-tos",
            "--register-unsafely-without-email",
            "--redirect",
            "--keep-until-expiring",
            "-d",
            hostname,
        ],
        timeout=180,
    )
    ok = certificate["returncode"] == 0
    log_event(
        "hosting-domain-applied",
        request_id=request_id,
        hostname=hostname,
        tenant_slug=tenant_slug,
        workspace_key=workspace_key,
        ok=ok,
    )
    return {
        "ok": ok,
        "status": "succeeded" if ok else "blocked",
        "applied": ok,
        "error": None if ok else "acme_certificate_failed",
        "result": {
            "hostname": hostname,
            "http_route_configured": True,
            "tls": "active" if ok else "pending",
            "certificate_output": str(certificate.get("stdout") or "")[-1000:],
            "certificate_error": str(certificate.get("stderr") or "")[-1000:],
        },
    }


def dispatch(payload: dict[str, Any]) -> dict[str, object]:
    supplied = str(payload.get("token") or "")
    if not TOKEN or not hmac.compare_digest(supplied, TOKEN):
        return {"ok": False, "error": "unauthorized"}
    operation = str(payload.get("operation") or "")
    request_id = str(payload.get("request_id") or "")[:160]
    if operation == "status":
        return cached_status()
    if operation == "repair":
        return execute_action(
            str(payload.get("action") or ""),
            payload.get("apply") is True,
            request_id,
        )
    if operation == "hosting_domain_apply":
        return apply_hosting_domain(payload, request_id)
    return {"ok": False, "error": "operation_not_allowed"}


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(MAX_REQUEST_BYTES + 1)
        if not raw or len(raw) > MAX_REQUEST_BYTES:
            response = {"ok": False, "error": "request_too_large"}
        else:
            try:
                payload = json.loads(raw)
                response = dispatch(payload) if isinstance(payload, dict) else {"ok": False, "error": "invalid_request"}
            except (UnicodeDecodeError, json.JSONDecodeError):
                response = {"ok": False, "error": "invalid_json"}
            except (OSError, ValueError, TypeError, IndexError, KeyError) as exc:
                log_event("handler-error", error=type(exc).__name__)
                response = {"ok": False, "error": "internal_agent_error"}
        self.wfile.write(json.dumps(response, ensure_ascii=False, default=str).encode() + b"\n")


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


class TCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    if len(TOKEN) < 32:
        raise SystemExit("WAREHOUSE_SHIELD_AGENT_TOKEN must be at least 32 characters")
    if not 0 <= TCP_PORT <= 65535:
        raise SystemExit("WAREHOUSE_SHIELD_AGENT_TCP_PORT is invalid")
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOCKET_PATH.unlink(missing_ok=True)
    with Server(str(SOCKET_PATH), Handler) as server:
        os.chmod(SOCKET_PATH, 0o660)
        tcp_server = TCPServer((TCP_HOST, TCP_PORT), Handler) if TCP_HOST and TCP_PORT else None
        tcp_thread: threading.Thread | None = None
        if tcp_server is not None:
            tcp_thread = threading.Thread(
                target=tcp_server.serve_forever,
                kwargs={"poll_interval": 0.5},
                daemon=True,
            )
            tcp_thread.start()
        log_event(
            "agent-started",
            socket=str(SOCKET_PATH),
            tcp_host=TCP_HOST or None,
            tcp_port=TCP_PORT or None,
            apply_enabled=APPLY_ENABLED,
        )
        try:
            server.serve_forever(poll_interval=0.5)
        finally:
            if tcp_server is not None:
                tcp_server.shutdown()
                tcp_server.server_close()
            if tcp_thread is not None:
                tcp_thread.join(timeout=2)


if __name__ == "__main__":
    main()
