from __future__ import annotations

import importlib.util
import json
from collections import namedtuple
from pathlib import Path


def _load_agent():
    path = Path(__file__).resolve().parents[2] / "ops/server/warehouse-shield-agent.py"
    spec = importlib.util.spec_from_file_location("warehouse_shield_agent_storage_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_storage_sample_keeps_root_compatibility_and_reports_data_volume(
    monkeypatch, tmp_path: Path
) -> None:
    agent = _load_agent()
    usage = namedtuple("usage", "total used free")
    data_mount = tmp_path / "warehouse-data"
    data_mount.mkdir()
    data_device = tmp_path / "vdb1"
    data_device.touch()
    monkeypatch.setattr(agent, "DATA_MOUNTPOINT", data_mount)
    monkeypatch.setattr(agent, "DATA_DEVICE", str(data_device))
    monkeypatch.setattr(agent, "DATA_VOLUME_REQUIRED", True)
    monkeypatch.setattr(
        agent.os.path,
        "ismount",
        lambda value: str(value) in {"/", str(data_mount)},
    )
    monkeypatch.setattr(
        agent.shutil,
        "disk_usage",
        lambda value: usage(200, 50, 150) if str(value) == "/" else usage(40, 10, 30),
    )

    def fake_run(arguments: list[str], timeout: float = 15.0) -> dict[str, object]:
        target = arguments[-1]
        filesystem = {
            "source": "/dev/vda2" if target == "/" else str(data_device),
            "target": target,
            "fstype": "ext4",
            "uuid": "root-uuid" if target == "/" else "data-uuid",
            "label": "" if target == "/" else "warehouse-data",
            "options": "rw,relatime",
        }
        return {
            "returncode": 0,
            "stdout": json.dumps({"filesystems": [filesystem]}),
            "stderr": "",
        }

    monkeypatch.setattr(agent, "run_fixed", fake_run)
    storage = agent.storage_sample()

    assert storage["total_bytes"] == 200
    assert storage["used_bytes"] == 50
    assert storage["free_bytes"] == 150
    assert storage["used_pct"] == 25.0
    assert [volume["id"] for volume in storage["volumes"]] == [
        "root",
        "warehouse-data",
    ]
    data = storage["volumes"][1]
    assert data == {
        "id": "warehouse-data",
        "label": "Warehouse data",
        "mountpoint": str(data_mount),
        "expected_device": str(data_device),
        "device": str(data_device),
        "device_present": True,
        "device_matches": True,
        "filesystem": "ext4",
        "filesystem_label": "warehouse-data",
        "uuid": "data-uuid",
        "options": "rw,relatime",
        "mounted": True,
        "required": True,
        "available": True,
        "state": "mounted",
        "total_bytes": 40,
        "used_bytes": 10,
        "free_bytes": 30,
        "used_pct": 25.0,
    }
    assert agent.storage_alerts(storage) == []


def test_required_data_volume_has_independent_mount_and_capacity_alerts(
    monkeypatch, tmp_path: Path
) -> None:
    agent = _load_agent()
    data_mount = tmp_path / "warehouse-data"
    data_mount.mkdir()
    data_device = tmp_path / "vdb1"
    data_device.touch()
    monkeypatch.setattr(agent, "DATA_MOUNTPOINT", data_mount)
    monkeypatch.setattr(agent, "DATA_DEVICE", str(data_device))
    monkeypatch.setattr(agent, "DATA_VOLUME_REQUIRED", True)
    monkeypatch.setattr(agent.os.path, "ismount", lambda value: str(value) == "/")
    monkeypatch.setattr(
        agent.shutil,
        "disk_usage",
        lambda _value: namedtuple("usage", "total used free")(200, 20, 180),
    )
    monkeypatch.setattr(
        agent,
        "run_fixed",
        lambda _arguments, timeout=15.0: {
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "filesystems": [
                        {
                            "source": "/dev/vda2",
                            "target": "/",
                            "fstype": "ext4",
                            "options": "rw,relatime",
                        }
                    ]
                }
            ),
            "stderr": "",
        },
    )

    storage = agent.storage_sample()
    data = storage["volumes"][1]
    assert data["state"] == "unmounted"
    assert data["mounted"] is False
    assert [alert["code"] for alert in agent.storage_alerts(storage)] == ["data-volume-unmounted"]

    data.update(
        {
            "mounted": True,
            "available": True,
            "state": "mounted",
            "used_pct": 91.5,
        }
    )
    assert [alert["code"] for alert in agent.storage_alerts(storage)] == ["data-volume-pressure"]


def test_custom_domain_agent_rejects_an_existing_server_name(monkeypatch, tmp_path: Path) -> None:
    agent = _load_agent()
    available = tmp_path / "available"
    enabled = tmp_path / "enabled"
    available.mkdir()
    enabled.mkdir()
    existing = available / "existing.conf"
    existing.write_text("server { server_name app.example.com; }", encoding="utf-8")
    (enabled / "existing.conf").symlink_to(existing)
    monkeypatch.setattr(agent, "NGINX_DOMAIN_AVAILABLE", available)
    monkeypatch.setattr(agent, "NGINX_DOMAIN_ENABLED", enabled)

    result = agent.apply_hosting_domain(
        {
            "hostname": "app.example.com",
            "tenant_slug": "bonfire",
            "workspace_key": "project-api",
        },
        "request-1",
    )

    assert result == {
        "ok": False,
        "status": "blocked",
        "error": "hostname_already_configured_on_host",
    }


def test_custom_domain_agent_writes_route_and_observes_tls(monkeypatch, tmp_path: Path) -> None:
    agent = _load_agent()
    available = tmp_path / "available"
    enabled = tmp_path / "enabled"
    available.mkdir()
    enabled.mkdir()
    monkeypatch.setattr(agent, "NGINX_DOMAIN_AVAILABLE", available)
    monkeypatch.setattr(agent, "NGINX_DOMAIN_ENABLED", enabled)
    monkeypatch.setattr(agent.shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(
        agent,
        "run_fixed",
        lambda arguments, timeout=15.0: {
            "returncode": 0,
            "stdout": "certificate active" if arguments[0] == "certbot" else "",
            "stderr": "",
        },
    )
    monkeypatch.setattr(agent, "log_event", lambda *args, **kwargs: None)

    result = agent.apply_hosting_domain(
        {
            "hostname": "app.example.com",
            "tenant_slug": "bonfire",
            "workspace_key": "project-api",
        },
        "request-2",
    )

    assert result["status"] == "succeeded"
    assert result["result"]["tls"] == "active"
    configuration = (available / "warehouse-hosting-app.example.com.conf").read_text()
    assert "server_name app.example.com;" in configuration
    assert "rewrite ^/(.*)$ /assets/bonfire/project-api/$1 break;" in configuration
