from __future__ import annotations

import json

from sqlalchemy import text

from app.api.deps import ActorContext
from app.db.session import tenant_session


def map_zones_payload(actor: ActorContext) -> dict[str, list[dict[str, object]]]:
    """Preserve the existing GET /api/map/zones shape using PostgreSQL only."""
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            text(
                """
                SELECT mz.id, mz.warehouse_id, mz.zone_id, w.name AS warehouse_name,
                       z.zone_code, z.zone_name, mz.name, mz.kind, mz.floor_no,
                       mz.geojson, mz.color, mz.note, mz.created_at
                FROM warehouse.map_zones AS mz
                LEFT JOIN warehouse.warehouses AS w ON w.id = mz.warehouse_id
                LEFT JOIN warehouse.warehouse_zones AS z ON z.id = mz.zone_id
                WHERE mz.active
                ORDER BY mz.created_at DESC, mz.id DESC
                """
            )
        ).mappings().all()
    zones: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        raw_geojson = item.get("geojson")
        if isinstance(raw_geojson, str):
            try:
                item["geojson"] = json.loads(raw_geojson)
            except json.JSONDecodeError:
                item["geojson"] = None
        zones.append(item)
    return {"zones": zones}
