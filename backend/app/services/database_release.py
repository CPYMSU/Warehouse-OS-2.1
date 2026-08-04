"""Database evidence gate shared by automatic and manual deployment activation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text

WORKSPACE_MANAGED_DATABASE_MODES = frozenset({"workspace_managed", "none"})


def workspace_database_policy(config: object) -> dict[str, object]:
    workspace_config = config if isinstance(config, dict) else {}
    supplied = workspace_config.get("database_policy")
    policy = supplied if isinstance(supplied, dict) else {}
    mode = str(policy.get("mode") or "platform_managed").strip().lower()
    if mode not in {
        "platform_managed",
        "external",
        "workspace_managed",
        "none",
    }:
        mode = "platform_managed"
    return {
        "mode": mode,
        "platform_database_injected": mode in {"platform_managed", "external"},
        "platform_release_gate": mode == "platform_managed",
        "workspace_services_allowed": True,
    }


def observe_database_release_gate(
    session: Any,
    workspace_id: object,
) -> dict[str, object]:
    """Return durable evidence required before routing a database-backed release."""

    resolved_workspace_id = UUID(str(workspace_id))
    workspace_config = session.execute(
        text("SELECT config FROM digital_asset.workspaces WHERE id=:workspace_id"),
        {"workspace_id": resolved_workspace_id},
    ).scalar_one_or_none()
    policy = workspace_database_policy(workspace_config)
    if str(policy["mode"]) in WORKSPACE_MANAGED_DATABASE_MODES:
        return {
            "required": False,
            "ready": True,
            "reason": "database_lifecycle_is_workspace_managed",
            "policy": policy,
        }
    if str(policy["mode"]) == "external":
        return {
            "required": False,
            "ready": True,
            "reason": "external_database_lifecycle_is_customer_managed",
            "policy": policy,
        }
    binding = (
        session.execute(
            text(
                """
                SELECT id,status,provider_key,capabilities,config
                FROM digital_asset.database_bindings
                WHERE workspace_id=:workspace_id AND is_default
                ORDER BY created_at LIMIT 1
                """
            ),
            {"workspace_id": resolved_workspace_id},
        )
        .mappings()
        .one_or_none()
    )
    if binding is None:
        return {
            "required": False,
            "ready": True,
            "reason": "workspace_has_no_default_database",
            "policy": policy,
        }
    migrations = [
        dict(row)
        for row in session.execute(
            text(
                """
                SELECT resource_key,status,desired_state,observed_state,last_error
                FROM digital_asset.hosting_resources
                WHERE workspace_id=:workspace_id
                  AND resource_kind='database_migration'
                ORDER BY created_at
                """
            ),
            {"workspace_id": resolved_workspace_id},
        ).mappings()
    ]
    if not migrations:
        return {
            "required": False,
            "ready": True,
            "reason": "no_database_migration_declared",
            "database_binding_id": str(binding["id"]),
            "policy": policy,
        }
    migration_evidence = []
    migrations_ready = True
    for migration in migrations:
        observed = (
            dict(migration["observed_state"])
            if isinstance(migration.get("observed_state"), dict)
            else {}
        )
        applied = (
            str(migration.get("status") or "") == "ready"
            and bool(observed.get("transactional"))
            and not bool(observed.get("planned"))
        )
        migrations_ready = migrations_ready and applied
        migration_evidence.append(
            {
                "version": str(migration.get("resource_key") or ""),
                "ready": applied,
                "status": migration.get("status"),
                "checksum": observed.get("checksum")
                or (migration.get("desired_state") or {}).get("checksum"),
                "history_id": observed.get("history_id"),
                "backup_id": observed.get("backup_id"),
                "error": migration.get("last_error"),
            }
        )
    backup = (
        session.execute(
            text(
                """
                SELECT id,sha256,metadata,completed_at
                FROM digital_asset.database_backups
                WHERE workspace_id=:workspace_id
                  AND database_binding_id=:database_id
                  AND status='ready'
                ORDER BY completed_at DESC NULLS LAST,created_at DESC
                LIMIT 1
                """
            ),
            {
                "workspace_id": resolved_workspace_id,
                "database_id": binding["id"],
            },
        )
        .mappings()
        .one_or_none()
    )
    metadata = (
        dict(backup["metadata"])
        if backup is not None and isinstance(backup.get("metadata"), dict)
        else {}
    )
    backup_ready = bool(
        backup is not None
        and backup.get("sha256")
        and metadata.get("checksum_verified")
        and metadata.get("restore_verified")
    )
    capabilities = (
        dict(binding["capabilities"])
        if isinstance(binding.get("capabilities"), dict)
        else {}
    )
    provider_ready = str(binding.get("status") or "") == "ready"
    vector_ready = bool(capabilities.get("vector_extension"))
    ready = provider_ready and vector_ready and backup_ready and migrations_ready
    blockers = []
    if not provider_ready:
        blockers.append("database_binding_not_ready")
    if not vector_ready:
        blockers.append("vector_extension_not_observed")
    if not backup_ready:
        blockers.append("verified_backup_missing")
    if not migrations_ready:
        blockers.append("database_migration_not_applied")
    return {
        "required": True,
        "ready": ready,
        "database_binding_id": str(binding["id"]),
        "provider": binding["provider_key"],
        "policy": policy,
        "capabilities": capabilities,
        "backup": (
            {
                "backup_id": str(backup["id"]),
                "sha256": str(backup["sha256"]),
                "checksum_verified": bool(metadata.get("checksum_verified")),
                "restore_verified": bool(metadata.get("restore_verified")),
                "completed_at": backup["completed_at"],
            }
            if backup is not None
            else None
        ),
        "migrations": migration_evidence,
        "blockers": blockers,
    }
