from __future__ import annotations

import os
import platform
import socket
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.db.session import database_is_available

router = APIRouter(tags=["system"])


def _csv(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def _identity() -> dict[str, object]:
    return {
        "schema": "warehouse.cluster-node.v1",
        "node_id": os.getenv("WAREHOUSE_NODE_ID", socket.gethostname()),
        "node_role": os.getenv("WAREHOUSE_NODE_ROLE", "standalone"),
        "release_id": os.getenv("WAREHOUSE_RELEASE_ID", "unknown"),
        "git_sha": os.getenv("WAREHOUSE_GIT_SHA", "unknown"),
        "alembic_head": os.getenv("WAREHOUSE_ALEMBIC_HEAD", "unknown"),
        "platform": os.getenv(
            "WAREHOUSE_NODE_PLATFORM",
            f"{platform.system().lower()}-{platform.machine().lower()}",
        ),
        "peers": _csv("WAREHOUSE_CLUSTER_PEERS"),
    }


@router.get("/api/system/cluster")
def cluster_identity() -> dict[str, object]:
    return _identity()


@router.get("/api/system/readiness")
def cluster_readiness() -> dict[str, object]:
    database_ready = database_is_available()
    payload = {
        **_identity(),
        "status": "ready" if database_ready else "unready",
        "database": "ready" if database_ready else "unavailable",
        "observed_at": datetime.now(UTC).isoformat(),
    }
    if not database_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=payload,
        )
    return payload
