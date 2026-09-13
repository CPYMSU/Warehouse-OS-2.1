"""Source-only persistent transport with continuous bounded part scheduling.

No release, job, activation, or business endpoints are accepted. Secrets stay in memory.
"""

from __future__ import annotations

import concurrent.futures as futures
import http.client
import json
import math
import os
import re
import threading
import time
from urllib.parse import urlsplit

from source_delta import MAX_ARCHIVE, TransferError, read_bounded, require, safe_path, sha

PREFIX = "/api/workspaces/v1"
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


class UncertainTransfer(TransferError):
    pass


class SourceAPI:
    def __init__(self, base_url, token, *, observe=lambda _: None):
        url = urlsplit(base_url)
        require(
            url.scheme == "https" or (url.scheme == "http" and url.hostname == "127.0.0.1"),
            "unsafe_transport_origin",
        )
        require(
            url.hostname
            and not url.username
            and not url.password
            and url.path in {"", "/"}
            and not url.query
            and not url.fragment,
            "invalid_transport_origin",
        )
        self.url, self.token, self.observe = url, token, observe
        self.local, self.connections, self.lock = threading.local(), [], threading.Lock()

    def close(self):
        for connection in self.connections:
            connection.close()

    def call(self, method, path, *, payload=None, data=None, key=None):
        allowed = (
            (method == "GET" and path == PREFIX + "/sources")
            or (method == "POST" and path == PREFIX + "/source-uploads")
        )
        allowed |= bool(
            re.fullmatch(
                PREFIX
                + "/source-uploads/"
                + UUID
                + ({"GET": "", "PUT": r"/parts/[0-9]+", "POST": "/complete"}.get(method, "!")),
                path,
            )
        )
        require(allowed and "/download" not in path, "endpoint_refused")
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        elif data is not None:
            headers.update(
                {"Content-Type": "application/octet-stream", "Content-SHA256": sha(data)}
            )
        if key:
            headers["Idempotency-Key"] = key
        started = time.monotonic()
        connection = getattr(self.local, "connection", None)
        if connection is None:
            factory = (
                http.client.HTTPSConnection
                if self.url.scheme == "https"
                else http.client.HTTPConnection
            )
            connection = factory(self.url.hostname, self.url.port, timeout=180)
            self.local.connection = connection
            with self.lock:
                self.connections.append(connection)
        status = None
        try:
            connection.request(method, path, body=data, headers=headers)
            response = connection.getresponse()
            status = response.status
            raw = response.read(8 * 1024 * 1024 + 1)
            require(len(raw) <= 8 * 1024 * 1024, "response_size_limit")
            if status in {408, 429, 500, 502, 503, 504}:
                raise UncertainTransfer("retryable_http")
            require(200 <= status < 300, "nonrecoverable_http_" + str(status))
            return json.loads(raw) if raw else {}
        except (OSError, http.client.HTTPException):
            connection.close()
            raise UncertainTransfer("transport_uncertain") from None
        finally:
            self.observe(
                {
                    "method": method,
                    "status": status,
                    "bytes_sent": len(data or b""),
                    "elapsed_seconds": round(time.monotonic() - started, 4),
                }
            )


def _save(path, state):
    temporary = path.with_name(path.name + ".writing")
    require(not temporary.exists() and not temporary.is_symlink(), "checkpoint_partial_exists")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(state, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _read(api, path):
    for attempt in range(3):
        try:
            return api.call("GET", path)
        except UncertainTransfer:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def upload_source(
    api,
    archive,
    metadata,
    checkpoint,
    *,
    concurrency=4,
    budget_seconds=1200,
    progress=lambda _: None,
):
    """Reuse verified digest; otherwise resume one fixed session, persisting retries."""
    import fcntl

    require(type(concurrency) is int and 1 <= concurrency <= 4, "concurrency_limit")
    require(type(budget_seconds) is int and 1 <= budget_seconds <= 3600, "budget_limit")
    archive, checkpoint = safe_path(archive), safe_path(checkpoint)
    content = read_bounded(archive, MAX_ARCHIVE)
    digest, size = sha(content), len(content)
    del content
    require(
        digest == metadata["sha256"] and size == metadata["size_bytes"], "archive_binding_drift"
    )
    lock_path = safe_path(checkpoint.with_name(checkpoint.name + ".lock"))
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as locked:
        try:
            fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise TransferError("upload_already_running") from None
        return _upload_locked(
            api, archive, metadata, checkpoint, concurrency, budget_seconds, progress
        )


def _upload_locked(api, archive, metadata, checkpoint, concurrency, budget_seconds, progress):
    digest, size = metadata["sha256"], metadata["size_bytes"]
    sources = _read(api, PREFIX + "/sources").get("sources")
    require(isinstance(sources, list), "source_list_invalid")
    matches = [
        x for x in sources if x.get("artifact_sha256") == digest and x.get("state") == "verified"
    ]
    if matches:
        require(
            len(matches) == 1 and matches[0].get("size_bytes") == size, "existing_source_conflict"
        )
        return {"source": matches[0], "source_reused": True, "uploaded_bytes": 0}
    state = (
        json.loads(read_bounded(checkpoint, 1024 * 1024))
        if checkpoint.exists()
        else {
            "sha256": digest,
            "size_bytes": size,
            "create_attempts": 0,
            "complete_attempts": 0,
            "attempts": {},
            "spent_seconds": 0,
        }
    )
    require(
        state.get("sha256") == digest and state.get("size_bytes") == size,
        "checkpoint_binding_drift",
    )
    if not state.get("upload_id"):
        for _ in range(3):
            require(state["create_attempts"] < 3, "create_retry_limit")
            state["create_attempts"] += 1
            _save(checkpoint, state)
            try:
                doc = api.call(
                    "POST",
                    PREFIX + "/source-uploads",
                    payload={
                        "filename": archive.name,
                        "content_type": "application/octet-stream",
                        "size_bytes": size,
                        "sha256": digest,
                        "version_no": metadata["version_no"],
                        "component": "api",
                    },
                    key="source:" + digest,
                )
                upload_id = doc.get("upload_id")
                require(
                    isinstance(upload_id, str) and re.fullmatch(UUID, upload_id),
                    "upload_identity_invalid",
                )
                state["upload_id"] = upload_id
                _save(checkpoint, state)
                break
            except UncertainTransfer:
                continue
    require(state.get("upload_id"), "create_retry_limit")
    path = PREFIX + "/source-uploads/" + state["upload_id"]
    started, uploaded = time.monotonic(), 0
    initial_spent = state["spent_seconds"]
    pending = {}

    def put(part, chunk):
        with archive.open("rb") as stream:
            stream.seek(part * chunk)
            value = stream.read(chunk)
        api.call("PUT", path + "/parts/" + str(part), data=value)
        return len(value)

    try:
        with futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            while True:
                state["spent_seconds"] = round(initial_spent + time.monotonic() - started, 3)
                _save(checkpoint, state)
                doc = _read(api, path)
                require(
                    doc.get("upload_id") == state["upload_id"]
                    and doc.get("sha256") == digest
                    and doc.get("size_bytes") == size,
                    "upload_binding_drift",
                )
                chunk, count = doc.get("chunk_size_bytes"), doc.get("part_count")
                require(
                    type(chunk) is int
                    and 0 < chunk <= 16 * 1024 * 1024
                    and type(count) is int
                    and count == math.ceil(size / chunk),
                    "upload_geometry_drift",
                )
                received = doc.get("received_parts")
                require(
                    isinstance(received, list)
                    and all(type(i) is int and 0 <= i < count for i in received)
                    and len(received) == len(set(received)),
                    "received_parts_invalid",
                )
                if doc.get("status") == "verified":
                    result = (doc.get("result") or {}).get("archive") or {}
                    source = doc.get("source") or {}
                    require(
                        len(received) == count
                        and result.get("validated") is True
                        and result.get("files") == metadata["file_count"]
                        and source.get("uuid"),
                        "source_verification_failed",
                    )
                    rows = _read(api, PREFIX + "/sources").get("sources")
                    require(
                        isinstance(rows, list)
                        and any(
                            x.get("uuid") == source["uuid"]
                            and x.get("state") == "verified"
                            and x.get("artifact_sha256") == digest
                            and x.get("size_bytes") == size
                            for x in rows
                        ),
                        "source_readback_failed",
                    )
                    return {"source": source, "source_reused": False, "uploaded_bytes": uploaded}
                require(
                    doc.get("status")
                    in {"uploading", "created", "verifying", "processing", "assembling"},
                    "upload_terminal_or_unknown_state",
                )
                require(state["spent_seconds"] < budget_seconds, "upload_budget_exhausted")
                in_flight = set(pending.values())
                missing = [i for i in range(count) if i not in received and i not in in_flight]
                for part in missing[: max(0, concurrency - len(pending))]:
                    attempt = state["attempts"].get(str(part), 0)
                    require(attempt < 3, "part_retry_limit")
                    state["attempts"][str(part)] = attempt + 1
                    _save(checkpoint, state)
                    pending[pool.submit(put, part, chunk)] = part
                if pending:
                    done, _ = futures.wait(pending, timeout=10, return_when=futures.FIRST_COMPLETED)
                    # Process all completed failures before scheduling any replacements.
                    for future in done:
                        pending.pop(future)
                        try:
                            uploaded += future.result()
                        except UncertainTransfer:
                            pass  # Next iteration MUST read server state before any retry.
                elif len(received) == count:
                    if doc["status"] not in {"verifying", "processing", "assembling"}:
                        require(state["complete_attempts"] < 3, "complete_retry_limit")
                        state["complete_attempts"] += 1
                        _save(checkpoint, state)
                        try:
                            api.call("POST", path + "/complete", payload={})
                        except UncertainTransfer:
                            pass
                    time.sleep(0.2)
                progress(
                    {
                        "received_parts": len(received),
                        "part_count": count,
                        "in_flight": len(pending),
                        "spent_seconds": state["spent_seconds"],
                    }
                )
    finally:
        state["spent_seconds"] = round(initial_spent + time.monotonic() - started, 3)
        _save(checkpoint, state)
