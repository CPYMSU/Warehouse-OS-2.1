"""Bind an existing credential to MK5 only; never rotate keys or change scope."""

import json
import os
import re
import stat
import tempfile
from pathlib import Path

from source_delta import TransferError, pairs, read_bounded, require, safe_path
from source_git_receiver import workspace_info


def bind(path, key, verify=workspace_info):
    require(
        isinstance(key, str) and re.fullmatch(r"wak_[A-Za-z0-9_.-]+", key), "binding_key_invalid"
    )
    before = verify(key)
    path = safe_path(path)
    require(stat.S_IMODE(path.stat().st_mode) == 0o600, "binding_file_permissions_invalid")
    require(
        not stat.S_IMODE(path.parent.stat().st_mode) & 0o077,
        "binding_directory_permissions_invalid",
    )
    old = read_bounded(path, 128 * 1024)
    values = json.loads(old, object_pairs_hook=pairs)
    matches = [k for k in values if k in {"mk5", "mk5-ledger-system"}]
    if matches:
        require(len(matches) == 1 and values[matches[0]] == key, "existing_binding_conflict")
        return {"phase": "binding_verified", "reused": True, "other_bindings_preserved": True}
    values["mk5"] = key
    raw = json.dumps(values, sort_keys=True).encode()
    fd, name = tempfile.mkstemp(prefix=".mk5-binding-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        require(read_bounded(path, 128 * 1024) == old, "concurrent_binding_change")
        os.replace(name, path)
        actual = json.loads(read_bounded(path, 128 * 1024), object_pairs_hook=pairs)
        require(
            actual == values and stat.S_IMODE(path.stat().st_mode) == 0o600,
            "binding_readback_failed",
        )
        after = verify(actual["mk5"])
        require(
            before.get("active_deployment_id") == after.get("active_deployment_id"),
            "active_pointer_changed",
        )
        return {
            "phase": "binding_verified",
            "reused": False,
            "other_bindings_preserved": True,
            "credential_rotated": False,
            "permissions_expanded": False,
            "activation_requested": False,
        }
    finally:
        if os.path.exists(name):
            os.unlink(name)


if __name__ == "__main__":
    os.umask(0o077)
    try:
        value = os.environ.pop("MK5_BINDING_KEY", "")
        result = bind(
            Path.home() / "Server/bonfirework/secrets/digital-asset-workspace-keys.json", value
        )
        print(json.dumps(result, sort_keys=True))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": "stopped",
                    "error_code": str(exc)
                    if isinstance(exc, TransferError)
                    else type(exc).__name__,
                }
            )
        )
        raise SystemExit(1) from None
