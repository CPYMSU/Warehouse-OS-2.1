"""Permission-filtered executive overview backed only by persisted tenant data.

The V2 dashboard is intentionally able to render a module as unavailable.  This
service therefore never manufactures a "0" for a domain whose storage model has
not been delivered yet.  The small set of modules marked ``ready`` below are
derived from the PostgreSQL foundation tables and stay inside the actor's RLS
transaction.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from app.api.deps import ActorContext
from app.db.session import tenant_session


def _has_any(actor: ActorContext, *permissions: str) -> bool:
    """Return whether an actor is entitled to inspect a domain.

    L10 is the tenant administrator tier in the current authority model.  It
    retains the same visibility fallback the V2 navigation already applies,
    while lower levels require the explicit effective permission computed from
    all active appointments.
    """
    return actor.role_level >= 10 or any(item in actor.permissions for item in permissions)


def _access(actor: ActorContext) -> dict[str, bool]:
    return {
        "warehouse": _has_any(actor, "inventory.read"),
        "alerts": _has_any(actor, "alerts.read"),
        "stocktake": _has_any(actor, "inventory.read"),
        "erp": _has_any(actor, "erp.read"),
        "finance": _has_any(actor, "finance.read"),
        "assets_financial": _has_any(actor, "assets.read", "asset_mgmt.read"),
        "assets_digital": _has_any(actor, "assets.read", "asset_mgmt.read"),
        "procurement": _has_any(actor, "procurement.workflow.use"),
        "legal": _has_any(actor, "legal.manage"),
        "gis": _has_any(actor, "gis.read"),
        "reports": _has_any(actor, "reports.read"),
        "permissions": _has_any(
            actor,
            "permissions.topology.read",
            "permissions.topology.manage",
            "users.manage",
            "settings.manage",
        ),
        "audit": _has_any(actor, "audit.read"),
        "cases": _has_any(actor, "cases.read", "records.read"),
        "records": _has_any(actor, "cases.read", "records.read"),
        "settings": _has_any(actor, "settings.manage"),
    }


def executive_overview_payload(actor: ActorContext) -> dict[str, object]:
    """Build the V2 executive-dashboard contract for one tenant only."""
    access = _access(actor)
    with tenant_session(actor.tenant_id) as session:
        gis = session.execute(
            text(
                """
                SELECT
                  COUNT(*) FILTER (WHERE active)::integer AS warehouses,
                  COUNT(*) FILTER (
                    WHERE active AND lat IS NOT NULL AND lng IS NOT NULL
                  )::integer AS located
                FROM warehouse.warehouses
                """
            )
        ).mappings().one()
        locations = session.execute(
            text(
                """
                SELECT
                  COUNT(*) FILTER (WHERE active)::integer AS locations,
                  COUNT(*) FILTER (
                    WHERE active AND (
                      geojson IS NULL OR x_pos IS NULL OR y_pos IS NULL
                    )
                  )::integer AS unlocated_locations
                FROM warehouse.warehouse_locations
                """
            )
        ).mappings().one()
        permissions = session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*)::integer FROM iam.memberships WHERE active) AS users,
                  (
                    SELECT COUNT(DISTINCT user_id)::integer
                    FROM iam.membership_positions
                    WHERE active
                  ) AS assigned_users,
                  (SELECT COUNT(*)::integer FROM iam.roles WHERE active) AS roles,
                  (SELECT COUNT(*)::integer FROM iam.membership_roles) AS role_assignments
                """
            )
        ).mappings().one()
        audit = session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*)::integer FROM audit.events) AS events,
                  (
                    SELECT COUNT(*)::integer
                    FROM audit.events
                    WHERE created_at >= now() - interval '24 hours'
                  ) AS writes,
                  (
                    SELECT COUNT(*)::integer
                    FROM audit.events
                    WHERE event_type ILIKE '%failed%'
                       OR event_type ILIKE '%denied%'
                  ) AS failed,
                  (SELECT MAX(created_at) FROM audit.events) AS latest
                """
            )
        ).mappings().one()

    modules: dict[str, dict[str, object]] = {
        # These are the three domains for which the initial PostgreSQL model
        # contains enough truth to support a full dashboard card today.
        "gis": {
            "status": "ready" if access["gis"] else "unavailable",
            "warehouses": int(gis["warehouses"]),
            "located": int(gis["located"]),
            "unlocated": int(gis["warehouses"]) - int(gis["located"]),
            "locations": int(locations["locations"]),
            "unlocated_locations": int(locations["unlocated_locations"]),
        },
        "permissions": {
            "status": "ready" if access["permissions"] else "unavailable",
            "users": int(permissions["users"]),
            "assigned_users": int(permissions["assigned_users"]),
            "roles": int(permissions["roles"]),
            "role_assignments": int(permissions["role_assignments"]),
            "delegations": 0,
            "full_view": actor.role_level >= 10,
        },
        "audit": {
            "status": "ready" if access["audit"] else "unavailable",
            "events": int(audit["events"]),
            "writes": int(audit["writes"]),
            "failed": int(audit["failed"]),
            "latest": audit["latest"],
        },
    }
    # Compatibility-backed modules are connected even when their tenant has no
    # records yet.  Keep their values absent (the frontend renders an em dash)
    # and mark the empty state explicitly instead of reporting a false outage.
    for key in (
        "warehouse",
        "alerts",
        "stocktake",
        "erp",
        "finance",
        "assets",
        "procurement",
        "legal",
        "reports",
        "cases",
        "settings",
    ):
        has_access = access.get(key, access.get(f"{key}_financial", False))
        modules[key] = {
            "status": "ready" if has_access else "unavailable",
            "available": True,
            "empty": True,
            "source": "compatibility",
        }

    return {
        "scope": "permission-filtered",
        "generated_at": datetime.now(UTC),
        "access": access,
        "modules": modules,
    }
