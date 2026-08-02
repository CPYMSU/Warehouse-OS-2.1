"""Audited end-to-end hosting smoke runner for an immutable local archive.

This module is only invoked by the fixed server deployment manager inside the
active API container.  It provisions through domain services, then deliberately
uses the public workspace-key HTTP contract for storage, source and deployment.
No credential plaintext is printed or persisted outside the process.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import text

from app.api.deps import ActorContext
from app.core.config import get_settings
from app.db.session import system_session, tenant_session
from app.services.digital_asset_hosting import (
    WORKSPACE_ALL_SCOPES,
    create_asset,
    create_workspace,
    issue_workspace_key,
    revoke_workspace_key,
)


def _actor_for_tenant(tenant_slug: str) -> ActorContext:
    with system_session() as session:
        tenant = (
            session.execute(
                text(
                    """
                    SELECT id, slug, name, industry_template_key
                    FROM iam.tenants
                    WHERE slug=:slug AND status='active'
                    """
                ),
                {"slug": tenant_slug},
            )
            .mappings()
            .one_or_none()
        )
    if tenant is None:
        raise RuntimeError("Smoke tenant is unavailable")
    with tenant_session(tenant["id"]) as session:
        user = (
            session.execute(
                text(
                    """
                    SELECT u.id, u.username, u.display_name,
                           m.role_level, m.topology_level, m.topology_title
                    FROM iam.memberships AS m
                    JOIN iam.users AS u ON u.id=m.user_id
                    WHERE m.active AND u.active
                    ORDER BY m.role_level DESC, m.topology_level DESC, u.created_at
                    LIMIT 1
                    """
                )
            )
            .mappings()
            .one_or_none()
        )
    if user is None or int(user["role_level"]) < 10:
        raise RuntimeError("Smoke tenant has no active L10 operator")
    return ActorContext(
        user_id=UUID(str(user["id"])),
        tenant_id=UUID(str(tenant["id"])),
        tenant_slug=str(tenant["slug"]),
        tenant_name=str(tenant["name"]),
        industry_template_key=str(tenant["industry_template_key"]),
        username=str(user["username"]),
        display_name=str(user["display_name"]),
        role_level=int(user["role_level"]),
        topology_level=int(user["topology_level"]),
        topology_title=user["topology_title"],
        permissions=frozenset({"asset_mgmt.manage"}),
        auth_kind="hosting_smoke",
    )


def _resolve_or_create_workspace(
    actor: ActorContext,
    *,
    name: str,
    workspace_key: str,
    runtime_type: str,
) -> tuple[dict[str, object], dict[str, object], bool]:
    with tenant_session(actor.tenant_id) as session:
        existing = (
            session.execute(
                text(
                    """
                    SELECT w.id AS workspace_id, w.workspace_key,
                           a.id AS asset_id, a.asset_no, a.name
                    FROM digital_asset.workspaces AS w
                    JOIN digital_asset.assets AS a ON a.id=w.asset_id
                    WHERE w.workspace_key=:workspace_key
                    """
                ),
                {"workspace_key": workspace_key},
            )
            .mappings()
            .one_or_none()
        )
    if existing is not None:
        if str(existing["name"]).casefold() != name.casefold():
            raise RuntimeError("Workspace key belongs to a different asset")
        return (
            {
                "uuid": str(existing["asset_id"]),
                "asset_no": str(existing["asset_no"]),
                "name": str(existing["name"]),
            },
            {
                "uuid": str(existing["workspace_id"]),
                "workspace_key": str(existing["workspace_key"]),
            },
            False,
        )
    with tenant_session(actor.tenant_id) as session:
        existing_asset = (
            session.execute(
                text(
                    """
                    SELECT id, asset_no, name
                    FROM digital_asset.assets
                    WHERE lower(name)=lower(:name) AND status!='archived'
                    ORDER BY created_at
                    LIMIT 1
                    """
                ),
                {"name": name},
            )
            .mappings()
            .one_or_none()
        )
    if existing_asset is None:
        created = create_asset(
            actor,
            {
                "name": name,
                "asset_kind": "software",
                "summary": ("End-to-end hosted application verified by the platform smoke channel"),
                "tags": ["hosting-smoke", "warehouse-native"],
                "risk_level": "low",
            },
        )
        asset = created["asset"]
        asset_created = True
    else:
        asset = {
            "uuid": str(existing_asset["id"]),
            "asset_no": str(existing_asset["asset_no"]),
            "name": str(existing_asset["name"]),
        }
        asset_created = False
    workspace = create_workspace(
        actor,
        asset["uuid"],
        {
            "workspace_key": workspace_key,
            "runtime_type": "static" if runtime_type == "auto" else runtime_type,
            "service_plan": "hosted",
            "code_storage": "hdd",
        },
    )
    return asset, workspace["workspace"], asset_created


def _temporary_deploy_key(
    actor: ActorContext,
    workspace_id: object,
) -> tuple[str, str]:
    settings = get_settings()
    with tenant_session(actor.tenant_id) as session:
        active_primary = session.execute(
            text(
                """
                SELECT id FROM digital_asset.api_credentials
                WHERE workspace_id=:workspace_id AND key_kind='primary'
                  AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())
                LIMIT 1
                """
            ),
            {"workspace_id": workspace_id},
        ).scalar_one_or_none()
    if active_primary is None:
        primary = issue_workspace_key(
            actor,
            workspace_id,
            {"label": "Smoke bootstrap primary", "expires_days": 1},
            signing_secret=settings.integration_secret,
            key_kind="primary",
        )
        # The bootstrap primary is never transmitted or logged.  It merely
        # establishes the parent invariant required by delegated credentials.
        primary.pop("api_key", None)
    delegated = issue_workspace_key(
        actor,
        workspace_id,
        {
            "label": "One-time hosting smoke",
            "expires_days": 1,
            "scopes": list(WORKSPACE_ALL_SCOPES),
        },
        signing_secret=settings.integration_secret,
    )
    return str(delegated["api_key"]), str(delegated["credential_id"])


def _checked(response: httpx.Response) -> dict[str, Any]:
    if response.status_code >= 400:
        raise RuntimeError(
            f"Workspace API returned HTTP {response.status_code}: {response.text[:500]}"
        )
    value = response.json()
    if not isinstance(value, dict):
        raise RuntimeError("Workspace API returned a non-object response")
    return value


def run(args: argparse.Namespace) -> dict[str, object]:
    archive = Path(args.archive).resolve()
    if not archive.is_file():
        raise RuntimeError("Smoke source archive is missing")
    actor = _actor_for_tenant(args.tenant)
    asset, workspace, created = _resolve_or_create_workspace(
        actor,
        name=args.name,
        workspace_key=args.workspace_key,
        runtime_type=args.runtime_type,
    )
    api_key, credential_id = _temporary_deploy_key(actor, workspace["uuid"])
    headers = {"Authorization": f"Bearer {api_key}"}
    revoked = False
    try:
        with httpx.Client(base_url="http://127.0.0.1:8080", timeout=120) as client:
            storage = _checked(client.post("/api/workspaces/v1/storage/probe", headers=headers))
            with archive.open("rb") as source:
                uploaded = _checked(
                    client.post(
                        "/api/workspaces/v1/sources/upload",
                        headers=headers,
                        data={"version_no": args.version},
                        files={
                            "file": (
                                archive.name,
                                source,
                                "application/gzip",
                            )
                        },
                    )
                )
            source_id = str(uploaded["source"]["uuid"])
            configured = _checked(
                client.put(
                    "/api/workspaces/v1/runtime",
                    headers=headers,
                    json={
                        "runtime_type": args.runtime_type,
                        "source_version_id": source_id,
                        "component": args.component,
                        "entrypoint": args.entrypoint,
                        "deploy": True,
                        "idempotency_key": f"smoke-{source_id}-{time.time_ns()}",
                    },
                )
            )
            deployment_id = str(configured["deployment"]["uuid"])
            observed: dict[str, Any] = {}
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                observed = _checked(
                    client.get(
                        f"/api/workspaces/v1/deployments/{deployment_id}",
                        headers=headers,
                    )
                )["deployment"]
                if observed["status"] in {"ready", "failed", "cancelled"}:
                    break
                time.sleep(2)
            if observed.get("status") != "ready" or observed.get("health") != "healthy":
                raise RuntimeError(
                    "Hosting smoke did not become ready/healthy: "
                    + json.dumps(observed, ensure_ascii=False, default=str)[:1000]
                )
        public_url = str(observed["public_url"])
        with httpx.Client(timeout=30, follow_redirects=True) as public:
            page = public.get(public_url)
            page.raise_for_status()
            if args.expect_text not in page.text:
                raise RuntimeError("Public application content verification failed")
            api_probe = public.get(f"{get_settings().public_origin}/api/health")
            api_probe.raise_for_status()
        return {
            "ok": True,
            "asset": {
                "uuid": asset["uuid"],
                "asset_no": asset["asset_no"],
                "name": asset["name"],
                "created": created,
            },
            "workspace": {
                "uuid": workspace["uuid"],
                "workspace_key": workspace["workspace_key"],
            },
            "source_version_id": source_id,
            "deployment_id": deployment_id,
            "status": observed["status"],
            "health": observed["health"],
            "public_url": public_url,
            "storage": storage["observations"],
            "public_content_verified": True,
            "platform_api_verified": True,
        }
    finally:
        api_key = ""
        revoke_workspace_key(actor, workspace["uuid"], credential_id)
        revoked = True
        if not revoked:
            raise RuntimeError("Temporary smoke credential was not revoked")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Warehouse hosting smoke runner")
    result.add_argument("--archive", required=True)
    result.add_argument("--tenant", required=True)
    result.add_argument("--name", required=True)
    result.add_argument("--workspace-key", required=True)
    result.add_argument(
        "--runtime-type",
        choices=("auto", "static", "web", "api", "worker", "agent", "container", "compose"),
        default="auto",
    )
    result.add_argument("--component", default="frontend")
    result.add_argument("--entrypoint", default="index.html")
    result.add_argument("--version", default="smoke")
    result.add_argument("--expect-text", required=True)
    result.add_argument("--timeout", type=int, default=180)
    return result


def main() -> None:
    print(json.dumps(run(parser().parse_args()), ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
