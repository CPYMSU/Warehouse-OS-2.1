"""Single-purpose worker for isolated, version-pinned research computations."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import resource
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import get_engine, tenant_session

LOG_LIMIT = 256 * 1024
POLL_SECONDS = 1.0
_stopping = False


def _stop(_signum: int, _frame: object) -> None:
    global _stopping
    _stopping = True


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _claim(worker_id: str) -> tuple[UUID, UUID] | None:
    with get_engine().begin() as connection:
        row = (
            connection.execute(
                text("SELECT * FROM app.claim_next_research_execution(:worker_id)"),
                {"worker_id": worker_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    return row["job_id"], row["tenant_id"]


def _event(session, job: dict[str, object], event_type: str, message: str, **payload) -> None:
    session.execute(
        text(
            """
            INSERT INTO research.execution_events(
              tenant_id, project_id, job_id, event_type, message, payload
            ) VALUES (
              :tenant_id, :project_id, :job_id, :event_type, :message,
              CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "tenant_id": job["tenant_id"],
            "project_id": job["project_id"],
            "job_id": job["id"],
            "event_type": event_type,
            "message": message,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _job(tenant_id: UUID, job_id: UUID) -> dict[str, object] | None:
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text("SELECT * FROM research.execution_jobs WHERE id = :id FOR UPDATE"),
                {"id": job_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        item = dict(row)
        if item["status"] == "cancelled" or item["cancel_requested_at"] is not None:
            session.execute(
                text(
                    "UPDATE research.execution_jobs SET status = 'cancelled', "
                    "finished_at = COALESCE(finished_at, now()) WHERE id = :id"
                ),
                {"id": job_id},
            )
            _event(session, item, "cancelled", "Execution cancelled before start")
            return None
        return item


def _sandbox_uid(job_id: UUID) -> int:
    return 20000 + (int(job_id.hex[:8], 16) % 30000)


def _chown_tree(path: Path, uid: int, gid: int, *, directories: int, files: int) -> None:
    for root, dirnames, filenames in os.walk(path):
        root_path = Path(root)
        os.chown(root_path, 0, 0)
        root_path.chmod(directories)
        os.chown(root_path, uid, gid)
        for dirname in dirnames:
            child = root_path / dirname
            if child.is_symlink():
                raise RuntimeError("Symlinks are forbidden in execution packages")
        for filename in filenames:
            child = root_path / filename
            if child.is_symlink() or not child.is_file():
                raise RuntimeError("Only regular execution files are allowed")
            os.chown(child, 0, 0)
            child.chmod(files)
            os.chown(child, uid, gid)


def _preexec(uid: int, limits: dict[str, object]):
    def apply() -> None:
        os.setsid()
        os.setgroups([])
        os.setgid(uid)
        os.setuid(uid)
        os.umask(0o077)
        memory = int(limits["memory_mb"]) * 1024 * 1024
        cpu = int(limits["cpu_seconds"])
        output = int(limits["max_output_bytes"])
        processes = int(limits["max_processes"])
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 2))
        resource.setrlimit(resource.RLIMIT_FSIZE, (output, output))
        resource.setrlimit(resource.RLIMIT_NPROC, (processes, processes))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))

    return apply


def _cancel_requested(tenant_id: UUID, job_id: UUID) -> bool:
    with tenant_session(tenant_id) as session:
        row = session.execute(
            text(
                """
                UPDATE research.execution_jobs
                SET heartbeat_at = now()
                WHERE id = :id
                RETURNING cancel_requested_at
                """
            ),
            {"id": job_id},
        ).one()
    return row.cancel_requested_at is not None


def _terminate(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _excerpt(path: Path) -> str:
    data = path.read_bytes() if path.exists() else b""
    if len(data) > LOG_LIMIT:
        data = data[:LOG_LIMIT] + b"\n[log truncated]"
    return data.decode("utf-8", errors="replace")


def _artifacts(output_root: Path, limits: dict[str, object]) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    total = 0
    max_total = int(limits["max_output_bytes"])
    max_count = int(limits["max_artifacts"])
    for path in sorted(output_root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("Artifact symlinks are forbidden")
        if not path.is_file():
            continue
        if len(artifacts) >= max_count:
            raise RuntimeError("Artifact count limit exceeded")
        size = path.stat().st_size
        total += size
        if total > max_total:
            raise RuntimeError("Artifact byte limit exceeded")
        relative = path.relative_to(output_root).as_posix()
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        artifacts.append(
            {
                "id": uuid4(),
                "relative_path": relative,
                "content_type": mimetypes.guess_type(relative)[0] or "application/octet-stream",
                "content_sha256": digest.hexdigest(),
                "size_bytes": size,
            }
        )
    return artifacts


def _finish(
    tenant_id: UUID,
    job: dict[str, object],
    *,
    status_value: str,
    exit_code: int | None,
    stdout: str,
    stderr: str,
    artifacts: list[dict[str, object]],
    error: str | None = None,
) -> None:
    with tenant_session(tenant_id) as session:
        for artifact in artifacts:
            session.execute(
                text(
                    """
                    INSERT INTO research.execution_artifacts(
                      id, tenant_id, project_id, job_id, relative_path,
                      content_type, content_sha256, size_bytes
                    ) VALUES (
                      :id, :tenant_id, :project_id, :job_id, :relative_path,
                      :content_type, :content_sha256, :size_bytes
                    ) ON CONFLICT (tenant_id, project_id, job_id, relative_path)
                    DO UPDATE SET content_type = EXCLUDED.content_type,
                                  content_sha256 = EXCLUDED.content_sha256,
                                  size_bytes = EXCLUDED.size_bytes
                    """
                ),
                {
                    **artifact,
                    "tenant_id": tenant_id,
                    "project_id": job["project_id"],
                    "job_id": job["id"],
                },
            )
        summary = {
            "artifact_count": len(artifacts),
            "artifact_bytes": sum(int(item["size_bytes"]) for item in artifacts),
            "error": error,
        }
        session.execute(
            text(
                """
                UPDATE research.execution_jobs
                SET status = :status, exit_code = :exit_code,
                    stdout_excerpt = :stdout, stderr_excerpt = :stderr,
                    result_summary = CAST(:summary AS jsonb),
                    heartbeat_at = now(), finished_at = now()
                WHERE id = :id
                """
            ),
            {
                "status": status_value,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "summary": json.dumps(summary, ensure_ascii=False),
                "id": job["id"],
            },
        )
        _event(
            session,
            job,
            status_value,
            "Execution finished",
            exit_code=exit_code,
            artifacts=len(artifacts),
            error=error,
        )
        if job.get("run_id"):
            run_status = "completed" if status_value == "succeeded" else "failed"
            session.execute(
                text(
                    """
                    UPDATE research.runs
                    SET status = :run_status, completed_at = now(),
                        observations = observations || CAST(:observation AS jsonb)
                    WHERE id = :run_id
                    """
                ),
                {
                    "run_status": run_status,
                    "observation": json.dumps(
                        {
                            "execution_job_id": str(job["id"]),
                            "execution_status": status_value,
                            "artifact_count": len(artifacts),
                        }
                    ),
                    "run_id": job["run_id"],
                },
            )


def execute(tenant_id: UUID, job_id: UUID, worker_id: str) -> None:
    settings = get_settings()
    job = _job(tenant_id, job_id)
    if job is None:
        return
    job_root = (settings.research_execution_root.resolve() / "jobs" / str(job_id)).resolve()
    input_root = job_root / "inputs"
    output_root = job_root / "outputs"
    manifest_path = job_root / "manifest.json"
    stdout_path = job_root / "stdout.log"
    stderr_path = job_root / "stderr.log"
    tmp_root = job_root / "tmp"
    process: subprocess.Popen[bytes] | None = None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if hashlib.sha256(_canonical(manifest)).hexdigest() != str(job["manifest_sha256"]):
            raise RuntimeError("Execution manifest checksum mismatch")
        if str(manifest.get("job_id")) != str(job_id):
            raise RuntimeError("Execution manifest identity mismatch")
        if output_root.exists():
            shutil.rmtree(output_root)
        output_root.mkdir(mode=0o700)
        if tmp_root.exists():
            shutil.rmtree(tmp_root)
        tmp_root.mkdir(mode=0o700)
        uid = _sandbox_uid(job_id)
        job_root.chmod(0o711)
        _chown_tree(input_root, uid, uid, directories=0o500, files=0o400)
        _chown_tree(output_root, uid, uid, directories=0o700, files=0o600)
        _chown_tree(tmp_root, uid, uid, directories=0o700, files=0o600)
        entrypoint = (input_root / str(job["entrypoint"])).resolve()
        entrypoint.relative_to(input_root)
        if not entrypoint.is_file() or entrypoint.is_symlink():
            raise RuntimeError("Execution entrypoint is unavailable")
        limits = dict(job["resource_limits"])
        command = ["/usr/local/bin/python", "-B", str(entrypoint), *list(job["arguments"])]
        environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "HOME": str(tmp_root),
            "TMPDIR": str(tmp_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "RESEARCH_JOB_ID": str(job_id),
            "RESEARCH_INPUT_DIR": str(input_root),
            "RESEARCH_OUTPUT_DIR": str(output_root),
            "RESEARCH_MANIFEST_SHA256": str(job["manifest_sha256"]),
        }
        with tenant_session(tenant_id) as session:
            session.execute(
                text(
                    "UPDATE research.execution_jobs SET status = 'running', "
                    "started_at = now(), heartbeat_at = now() WHERE id = :id"
                ),
                {"id": job_id},
            )
            _event(
                session,
                job,
                "started",
                "Isolated executor started",
                worker_id=worker_id,
                runtime=job["runtime"],
            )
        started = time.monotonic()
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            process = subprocess.Popen(
                command,
                cwd=input_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                preexec_fn=_preexec(uid, limits),
            )
            outcome = "running"
            while process.poll() is None:
                if _stopping or _cancel_requested(tenant_id, job_id):
                    outcome = "cancelled"
                    _terminate(process)
                    break
                if time.monotonic() - started > int(limits["timeout_seconds"]):
                    outcome = "timed_out"
                    _terminate(process)
                    break
                time.sleep(POLL_SECONDS)
        exit_code = process.returncode
        if outcome == "running":
            outcome = "succeeded" if exit_code == 0 else "failed"
        artifacts = _artifacts(output_root, limits)
        _finish(
            tenant_id,
            job,
            status_value=outcome,
            exit_code=exit_code,
            stdout=_excerpt(stdout_path),
            stderr=_excerpt(stderr_path),
            artifacts=artifacts,
        )
    except Exception as exc:
        if process is not None and process.poll() is None:
            _terminate(process)
        _finish(
            tenant_id,
            job,
            status_value="failed",
            exit_code=process.returncode if process else None,
            stdout=_excerpt(stdout_path),
            stderr=_excerpt(stderr_path),
            artifacts=[],
            error=str(exc)[:1000],
        )


def main() -> None:
    if "--self-test" in sys.argv:
        _self_test()
        return
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    Path("/tmp/research-worker-ready").touch(mode=0o600, exist_ok=True)
    while not _stopping:
        try:
            claimed = _claim(worker_id)
        except SQLAlchemyError as exc:
            print(
                json.dumps(
                    {
                        "event": "research_executor.database_retry",
                        "error": type(exc).__name__,
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )
            time.sleep(3)
            continue
        if claimed is None:
            time.sleep(POLL_SECONDS)
            continue
        execute(claimed[1], claimed[0], worker_id)


def _self_test() -> None:
    """Exercise the deployed interpreter and privilege boundary without database data."""

    uid = 49999
    limits = {
        "memory_mb": 1024,
        "cpu_seconds": 15,
        "max_output_bytes": 1024 * 1024,
        "max_processes": 16,
    }
    with tempfile.TemporaryDirectory(prefix="research-executor-self-test-") as value:
        root = Path(value)
        root.chmod(0o711)
        inputs = root / "inputs"
        outputs = root / "outputs"
        temporary = root / "tmp"
        inputs.mkdir(mode=0o700)
        outputs.mkdir(mode=0o700)
        temporary.mkdir(mode=0o700)
        script = inputs / "main.py"
        script.write_text(
            """import os
import numpy as np
import pandas as pd
from scipy import stats

values = np.array([1.0, 2.0, 3.0])
frame = pd.DataFrame({"value": values})
frame["z"] = stats.zscore(values)
output = os.path.join(os.environ["RESEARCH_OUTPUT_DIR"], "result.csv")
frame.to_csv(output, index=False)
print("executor-self-test-ok")
""",
            encoding="utf-8",
        )
        _chown_tree(inputs, uid, uid, directories=0o500, files=0o400)
        _chown_tree(outputs, uid, uid, directories=0o700, files=0o600)
        _chown_tree(temporary, uid, uid, directories=0o700, files=0o600)
        completed = subprocess.run(
            ["/usr/local/bin/python", "-B", str(script)],
            cwd=inputs,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "HOME": str(temporary),
                "TMPDIR": str(temporary),
                "PYTHONDONTWRITEBYTECODE": "1",
                "RESEARCH_OUTPUT_DIR": str(outputs),
            },
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=30,
            preexec_fn=_preexec(uid, limits),
            check=False,
        )
        artifact = outputs / "result.csv"
        if completed.returncode != 0 or not artifact.is_file():
            raise RuntimeError(
                "Research executor self-test failed: "
                + completed.stderr.decode("utf-8", errors="replace")[:1000]
            )
        print(
            json.dumps(
                {
                    "ok": True,
                    "runtime": "python-3.13",
                    "sandbox_uid": uid,
                    "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
