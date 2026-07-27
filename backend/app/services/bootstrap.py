from __future__ import annotations

from sqlalchemy import text

from app.api.deps import ActorContext
from app.db.session import tenant_session
from app.services.templates import get_template_summary


def bootstrap_payload(actor: ActorContext) -> dict[str, object]:
    """Return real tenant state in the legacy bootstrap envelope.

    Empty collections mean the tenant has no corresponding PostgreSQL records;
    this function never injects demonstration rows.
    """
    with tenant_session(actor.tenant_id) as session:
        warehouses = session.execute(
            text(
                """
                SELECT id, code, name, warehouse_type, address, lat, lng,
                       storage_condition, capacity_usage, active, created_at, updated_at
                FROM warehouse.warehouses
                WHERE active
                ORDER BY name, code
                """
            )
        ).mappings().all()
        summary = session.execute(
            text(
                """
                SELECT
                  COUNT(*)::integer AS warehouse_count,
                  (SELECT COUNT(*)::integer FROM warehouse.warehouse_zones WHERE active)
                    AS zone_count,
                  (SELECT COUNT(*)::integer FROM warehouse.warehouse_locations WHERE active)
                    AS location_count
                FROM warehouse.warehouses
                WHERE active
                """
            )
        ).mappings().one()
    warehouse_rows = [dict(row) for row in warehouses]
    industry_template = get_template_summary(actor.industry_template_key)
    return {
        "tenant": {
            "id": str(actor.tenant_id),
            "slug": actor.tenant_slug,
            "name": actor.tenant_name,
        },
        "user": actor.user_payload,
        "INDUSTRY_TEMPLATE_KEY": actor.industry_template_key,
        "INDUSTRY_TEMPLATE": industry_template,
        "WAREHOUSES": [row["name"] for row in warehouse_rows],
        "warehouse_rows": warehouse_rows,
        "summary": dict(summary),
        "NAV_CONFIG": {"items": {}},
    }
