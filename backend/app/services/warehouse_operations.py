"""PostgreSQL implementation for the V2 warehouse workspaces.

The web client has several views over the same operational truth: items and
lots, receiving, issuing, inter-warehouse transit, GIS and the warehouse
pivot.  This module deliberately keeps those views behind one tenant-scoped
service instead of letting individual routes build incompatible snapshots.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import tenant_session


def _decimal(value: object, *, field: str = "quantity") -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field} must be a positive number",
        ) from exc
    if not result.is_finite() or result <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field} must be a positive number",
        )
    return result


def _float(value: object | None) -> float:
    return float(value) if value is not None else 0.0


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _permission(actor: ActorContext, *keys: str) -> bool:
    return actor.role_level >= 10 or any(key in actor.permissions for key in keys)


def _require(actor: ActorContext, *keys: str) -> None:
    if not _permission(actor, *keys):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _audit(
    session: Session, actor: ActorContext, event_type: str, payload: dict[str, object]
) -> None:
    session.execute(
        text(
            """
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (:tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb))
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "actor_user_id": actor.user_id,
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _warehouse(
    session: Session,
    value: str | None,
    *,
    required: bool = True,
    default_if_missing: bool = False,
) -> dict[str, object] | None:
    if not value or not value.strip():
        if default_if_missing:
            row = (
                session.execute(
                    text(
                        """
                        SELECT id, code, name
                        FROM warehouse.warehouses
                        WHERE active
                        ORDER BY created_at, name, code
                        LIMIT 1
                        """
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is not None:
                return dict(row)
        if required:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "No active warehouse is available"
                    if default_if_missing
                    else "A warehouse name or code is required"
                ),
            )
        return None
    row = (
        session.execute(
            text(
                """
            SELECT id, code, name
            FROM warehouse.warehouses
            WHERE active AND (lower(code) = lower(:value) OR lower(name) = lower(:value))
            ORDER BY name
            LIMIT 1
            """
            ),
            {"value": value.strip()},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Warehouse not found"
        )
    return dict(row)


def _item(session: Session, value: str) -> dict[str, object]:
    clean = value.strip()
    if not clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Item is required"
        )
    row = (
        session.execute(
            text(
                """
            SELECT i.id, i.name, i.item_code, i.unit, i.unit_price, i.perishable,
                   i.default_shelf_life_days, i.required_storage_condition
            FROM warehouse.items AS i
            WHERE i.active
              AND (lower(i.name) = lower(:value) OR lower(i.item_code) = lower(:value))
            ORDER BY i.name
            LIMIT 1
            """
            ),
            {"value": clean},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Item not found. Create the item before posting stock movement.",
        )
    return dict(row)


def _item_category(session: Session, value: object | None) -> dict[str, object] | None:
    clean = str(value or "").strip()
    if not clean:
        return None
    try:
        category_id: UUID | None = UUID(clean)
    except ValueError:
        category_id = None
    row = (
        session.execute(
            text(
                """
                SELECT id, category_code, name
                FROM warehouse.item_categories
                WHERE active
                  AND (
                    (CAST(:category_id AS uuid) IS NOT NULL AND id = CAST(:category_id AS uuid))
                    OR lower(category_code) = lower(:value)
                    OR lower(name) = lower(:value)
                  )
                ORDER BY name
                LIMIT 1
                """
            ),
            {"category_id": category_id, "value": clean},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Item category not found",
        )
    return dict(row)


def _item_for_edit(
    session: Session, *, item_id: object | None = None, name: object | None = None
) -> dict[str, object]:
    clean_id = str(item_id or "").strip()
    clean_name = str(name or "").strip()
    parsed_id: UUID | None = None
    if clean_id:
        try:
            parsed_id = UUID(clean_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Item id must be a UUID",
            ) from exc
    if parsed_id is None and not clean_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Item id or name is required",
        )
    row = (
        session.execute(
            text(
                """
                SELECT id, item_code, name, model, unit, unit_price, category_id, active
                FROM warehouse.items
                WHERE (
                    CAST(:item_id AS uuid) IS NOT NULL
                    AND id = CAST(:item_id AS uuid)
                  )
                   OR (
                    CAST(:item_id AS uuid) IS NULL
                    AND lower(name) = lower(:name)
                  )
                ORDER BY active DESC, created_at
                LIMIT 1
                """
            ),
            {"item_id": parsed_id, "name": clean_name},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return dict(row)


def _new_no(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC):%Y%m%d}-{uuid4().hex[:7].upper()}"


def _available_lots(
    session: Session, item_id: UUID, warehouse_id: UUID | None = None
) -> list[dict[str, object]]:
    conditions = "AND warehouse_id = :warehouse_id" if warehouse_id is not None else ""
    rows = (
        session.execute(
            text(
                f"""
            SELECT id, warehouse_id, batch_no, expires_at, quantity_on_hand
            FROM warehouse.stock_lots
            WHERE item_id = :item_id AND active AND quantity_on_hand > 0 {conditions}
            ORDER BY expires_at NULLS LAST, created_at, id
            FOR UPDATE
            """
            ),
            {"item_id": item_id, "warehouse_id": warehouse_id},
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def _consume_lots(
    session: Session,
    *,
    item_id: UUID,
    quantity: Decimal,
    warehouse_id: UUID | None = None,
) -> list[tuple[dict[str, object], Decimal]]:
    lots = _available_lots(session, item_id, warehouse_id)
    if sum(Decimal(str(row["quantity_on_hand"])) for row in lots) < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Insufficient available stock"
        )
    remaining = quantity
    consumed: list[tuple[dict[str, object], Decimal]] = []
    for lot in lots:
        take = min(remaining, Decimal(str(lot["quantity_on_hand"])))
        if take <= 0:
            continue
        session.execute(
            text(
                "UPDATE warehouse.stock_lots "
                "SET quantity_on_hand = quantity_on_hand - :quantity "
                "WHERE id = :id"
            ),
            {"quantity": take, "id": lot["id"]},
        )
        consumed.append((lot, take))
        remaining -= take
        if remaining == 0:
            break
    return consumed


def _insert_ledger(
    session: Session,
    *,
    actor: ActorContext,
    item_id: UUID,
    lot_id: UUID | None,
    warehouse_id: UUID | None,
    movement_type: str,
    quantity_delta: Decimal,
    source_type: str,
    source_id: UUID,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO warehouse.stock_ledger(
              id, tenant_id, item_id, lot_id, warehouse_id, movement_type,
              quantity_delta, source_type, source_id, created_by
            ) VALUES (
              :id, :tenant_id, :item_id, :lot_id, :warehouse_id, :movement_type,
              :quantity_delta, :source_type, :source_id, :created_by
            )
            """
        ),
        {
            "id": uuid4(),
            "tenant_id": actor.tenant_id,
            "item_id": item_id,
            "lot_id": lot_id,
            "warehouse_id": warehouse_id,
            "movement_type": movement_type,
            "quantity_delta": quantity_delta,
            "source_type": source_type,
            "source_id": source_id,
            "created_by": actor.user_id,
        },
    )


def _rows_for_inventory(session: Session) -> list[dict[str, object]]:
    rows = (
        session.execute(
            text(
                """
            SELECT i.id AS item_id, i.item_code, i.name, i.model, i.unit,
                   i.safe_quantity, i.unit_price, i.supplier_name, i.critical,
                   i.perishable, i.required_storage_condition, c.id AS category_id,
                   c.category_code, c.name AS category_name, c.requires_return,
                   w.id AS warehouse_id, w.name AS warehouse_name,
                   COALESCE(SUM(l.quantity_on_hand), 0) AS stock,
                   MIN(l.expires_at) FILTER (WHERE l.quantity_on_hand > 0) AS expires_at,
                   string_agg(DISTINCT loc.location_code, ' / ')
                     FILTER (WHERE loc.location_code IS NOT NULL) AS locations
            FROM warehouse.items AS i
            LEFT JOIN warehouse.item_categories AS c
              ON c.tenant_id = i.tenant_id AND c.id = i.category_id
            LEFT JOIN warehouse.stock_lots AS l
              ON l.tenant_id = i.tenant_id AND l.item_id = i.id AND l.active
            LEFT JOIN warehouse.warehouses AS w
              ON w.tenant_id = l.tenant_id AND w.id = l.warehouse_id
            LEFT JOIN warehouse.warehouse_locations AS loc
              ON loc.tenant_id = l.tenant_id AND loc.id = l.location_id
            WHERE i.active
            GROUP BY i.id, c.id, w.id
            ORDER BY i.name, w.name NULLS LAST
            """
            )
        )
        .mappings()
        .all()
    )
    grouped: dict[UUID, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[row["item_id"]].append(dict(row))
    out: list[dict[str, object]] = []
    today = date.today()
    for item_rows in grouped.values():
        divisor = Decimal(len(item_rows))
        for row in item_rows:
            expires_at = row["expires_at"]
            expiry_days = (expires_at - today).days if expires_at else None
            safe = Decimal(str(row["safe_quantity"])) / divisor
            warehouse_id = row["warehouse_id"]
            out.append(
                {
                    "id": f"{row['item_id']}:{warehouse_id or 'unassigned'}",
                    "itemId": str(row["item_id"]),
                    "name": row["name"],
                    "code": row["item_code"],
                    "model": row["model"] or "—",
                    "unit": row["unit"],
                    "categoryId": str(row["category_id"]) if row["category_id"] else "",
                    "categoryCode": row["category_code"] or "",
                    "category": row["category_name"] or "—",
                    "stock": _float(row["stock"]),
                    "safe": _float(safe),
                    "unitPrice": _float(row["unit_price"]),
                    "wh": row["warehouse_name"] or "—",
                    "loc": row["locations"] or "—",
                    "supplier": row["supplier_name"] or "—",
                    "critical": bool(row["critical"]),
                    "perishable": bool(row["perishable"]),
                    "requiresReturn": bool(row["requires_return"]),
                    "expiryDays": expiry_days,
                    "hasTrendHistory": False,
                    "stockTrend": [],
                }
            )
    return out


def _inbound_rows(session: Session) -> list[dict[str, object]]:
    orders = (
        session.execute(
            text(
                """
            SELECT o.id, o.order_no, o.inbound_type, o.source_name, o.status,
                   o.received_at, u.display_name AS handler
            FROM warehouse.inbound_orders AS o
            LEFT JOIN iam.users AS u ON u.id = o.created_by
            ORDER BY o.received_at DESC, o.created_at DESC
            """
            )
        )
        .mappings()
        .all()
    )
    lines = (
        session.execute(
            text(
                """
            SELECT l.inbound_order_id, i.name, l.quantity, i.unit, l.batch_no,
                   l.quality_status, loc.location_code
            FROM warehouse.inbound_order_lines AS l
            JOIN warehouse.items AS i ON i.tenant_id = l.tenant_id AND i.id = l.item_id
            LEFT JOIN warehouse.warehouse_locations AS loc
              ON loc.tenant_id = l.tenant_id AND loc.id = l.location_id
            ORDER BY l.created_at, l.id
            """
            )
        )
        .mappings()
        .all()
    )
    line_map: dict[UUID, list[dict[str, object]]] = defaultdict(list)
    quality = {"qualified": "合格", "pending": "待檢", "rejected": "不合格"}
    for line in lines:
        line_map[line["inbound_order_id"]].append(
            {
                "name": line["name"],
                "qty": _float(line["quantity"]),
                "unit": line["unit"],
                "batch": line["batch_no"],
                "loc": line["location_code"] or "—",
                "quality": quality[line["quality_status"]],
            }
        )
    status_map = {
        "pending_review": "待審核",
        "quality_check": "質檢中",
        "received": "已入庫",
        "cancelled": "已取消",
    }
    return [
        {
            "id": str(order["id"]),
            "order_no": order["order_no"],
            "time": _iso(order["received_at"]),
            "type": order["inbound_type"],
            "source": order["source_name"] or "—",
            "handler": order["handler"] or "—",
            "status": status_map[order["status"]],
            "lines": line_map[order["id"]],
        }
        for order in orders
    ]


def _outbound_rows(session: Session) -> list[dict[str, object]]:
    orders = (
        session.execute(
            text(
                """
            SELECT id, order_no, use_type, department_name, target_name, urgent,
                   status, issued_at
            FROM warehouse.outbound_orders
            ORDER BY issued_at DESC, created_at DESC
            """
            )
        )
        .mappings()
        .all()
    )
    lines = (
        session.execute(
            text(
                """
            SELECT l.outbound_order_id, i.name, l.quantity, i.unit,
                   w.name AS warehouse_name
            FROM warehouse.outbound_order_lines AS l
            JOIN warehouse.items AS i ON i.tenant_id = l.tenant_id AND i.id = l.item_id
            LEFT JOIN warehouse.warehouses AS w
              ON w.tenant_id = l.tenant_id AND w.id = l.source_warehouse_id
            ORDER BY l.created_at, l.id
            """
            )
        )
        .mappings()
        .all()
    )
    line_map: dict[UUID, list[dict[str, object]]] = defaultdict(list)
    for line in lines:
        line_map[line["outbound_order_id"]].append(
            {
                "name": line["name"],
                "qty": _float(line["quantity"]),
                "unit": line["unit"],
                "loc": line["warehouse_name"] or "—",
            }
        )
    status_map = {"pending_approval": "審批中", "issued": "已出庫", "cancelled": "已取消"}
    return [
        {
            "id": str(order["id"]),
            "no": order["order_no"],
            "time": _iso(order["issued_at"]),
            "dept": order["department_name"] or "—",
            "target": order["target_name"] or "—",
            "use": order["use_type"],
            "urgent": bool(order["urgent"]),
            "status": status_map[order["status"]],
            "lines": line_map[order["id"]],
        }
        for order in orders
    ]


def _shipment_rows(session: Session) -> list[dict[str, object]]:
    rows = (
        session.execute(
            text(
                """
                SELECT s.shipment_no, s.quantity, s.batch_no, s.expires_at, s.status,
                       s.dispatched_at, s.eta_at, s.arrived_at, i.name AS item, i.unit,
                       i.required_storage_condition, source.name AS source_name,
                       destination.name AS destination_name
                FROM warehouse.shipments AS s
                JOIN warehouse.items AS i ON i.tenant_id = s.tenant_id AND i.id = s.item_id
                JOIN warehouse.warehouses AS source
                  ON source.tenant_id = s.tenant_id AND source.id = s.source_warehouse_id
                JOIN warehouse.warehouses AS destination
                  ON destination.tenant_id = s.tenant_id
                 AND destination.id = s.destination_warehouse_id
                ORDER BY s.dispatched_at DESC, s.created_at DESC
                """
            )
        )
        .mappings()
        .all()
    )
    now = datetime.now(UTC)
    output: list[dict[str, object]] = []
    for row in rows:
        eta = row["eta_at"]
        hours = None
        if eta is not None:
            hours = int((eta - now).total_seconds() // 3600)
        in_transit = row["status"] == "in_transit"
        output.append(
            {
                "shipmentNo": row["shipment_no"],
                "item": row["item"],
                "qty": _float(row["quantity"]),
                "unit": row["unit"],
                "batchNo": row["batch_no"],
                "expireAt": _iso(row["expires_at"]),
                "from": row["source_name"],
                "to": row["destination_name"],
                "status": row["status"],
                "delayed": bool(in_transit and eta is not None and eta < now),
                "hoursToEta": hours if in_transit else None,
                "eta": _iso(eta),
                "arrivedAt": _iso(row["arrived_at"]),
                "coldChain": bool(row["required_storage_condition"]),
            }
        )
    return output


def shipment_rows(actor: ActorContext) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        return _shipment_rows(session)


def _warehouse_hub(
    session: Session, actor: ActorContext, inventory: list[dict[str, object]]
) -> dict[str, object]:
    by_item: dict[str, dict[str, object]] = {}
    by_category: dict[str, dict[str, object]] = {}
    by_warehouse: dict[str, dict[str, object]] = {}
    for row in inventory:
        item = by_item.setdefault(
            row["itemId"],
            {"name": row["name"], "unit": row["unit"], "stock": 0.0, "safe": 0.0, "price": 0.0},
        )
        item["stock"] += _float(row["stock"])
        item["safe"] += _float(row["safe"])
        item["price"] = _float(row.get("unitPrice"))
        category = by_category.setdefault(
            row["category"] or "未分類", {"skus": set(), "value": 0.0}
        )
        category["skus"].add(row["itemId"])
        category["value"] += _float(row["stock"]) * _float(row.get("unitPrice"))
        warehouse = by_warehouse.setdefault(row["wh"] or "未分配", {"skus": set(), "value": 0.0})
        warehouse["skus"].add(row["itemId"])
        warehouse["value"] += _float(row["stock"]) * _float(row.get("unitPrice"))
    items = list(by_item.items())
    low = [item for _, item in items if item["stock"] > 0 and item["stock"] < item["safe"]]
    zero = [item for _, item in items if item["stock"] <= 0]
    stock_value = sum(item["stock"] * item["price"] for _, item in items)
    shipment_data = _shipment_rows(session)
    inbound_open = session.execute(
        text(
            "SELECT COUNT(*) FROM warehouse.inbound_orders "
            "WHERE status IN ('pending_review', 'quality_check')"
        )
    ).scalar_one()
    outbound_open = session.execute(
        text("SELECT COUNT(*) FROM warehouse.outbound_orders WHERE status = 'pending_approval'")
    ).scalar_one()
    recent_consumption = (
        session.execute(
            text(
                """
            SELECT i.id, i.name, i.unit, COALESCE(SUM(l.quantity), 0) AS quantity
            FROM warehouse.outbound_order_lines AS l
            JOIN warehouse.outbound_orders AS o
              ON o.tenant_id = l.tenant_id AND o.id = l.outbound_order_id
            JOIN warehouse.items AS i ON i.tenant_id = l.tenant_id AND i.id = l.item_id
            WHERE o.status = 'issued' AND o.issued_at >= now() - interval '90 days'
            GROUP BY i.id, i.name, i.unit
            ORDER BY quantity DESC, i.name
            LIMIT 8
            """
            )
        )
        .mappings()
        .all()
    )
    return {
        "scope": "permission-filtered",
        "generated_at": datetime.now(UTC),
        "access": {
            "inventory": _permission(actor, "inventory.read"),
            "inbound": _permission(actor, "inventory.inbound"),
            "outbound": _permission(actor, "inventory.outbound"),
            "shipments": _permission(actor, "inventory.shipment"),
        },
        "inventory": {
            "skus": len(items),
            "available_skus": sum(1 for _, item in items if item["stock"] > 0),
            "low_skus": len(low),
            "zero_skus": len(zero),
            "stock_value": stock_value,
            "turnover_90d": None,
        },
        "orders": {
            "inbound_open": int(inbound_open),
            "outbound_open": int(outbound_open),
            "urgent_outbound": 0,
        },
        "shipments": {
            "active": sum(1 for row in shipment_data if row["status"] == "in_transit"),
            "delayed": sum(1 for row in shipment_data if row["delayed"]),
            "due_24h": sum(
                1
                for row in shipment_data
                if row["status"] == "in_transit"
                and row["hoursToEta"] is not None
                and 0 <= row["hoursToEta"] <= 24
            ),
            "aging": [],
        },
        "category_mix": [
            {"label": label, "skus": len(value["skus"]), "value": value["value"]}
            for label, value in sorted(
                by_category.items(), key=lambda pair: (-len(pair[1]["skus"]), pair[0])
            )
        ],
        "warehouse_mix": [
            {"label": label, "skus": len(value["skus"]), "value": value["value"]}
            for label, value in sorted(
                by_warehouse.items(), key=lambda pair: (-len(pair[1]["skus"]), pair[0])
            )
        ],
        "flow": [],
        "coverage_trend": [],
        "consumption": [
            {
                "item_id": str(row["id"]),
                "name": row["name"],
                "unit": row["unit"],
                "quantity": _float(row["quantity"]),
                "turnover": _float(row["quantity"])
                / max(1.0, by_item.get(str(row["id"]), {}).get("stock", 0.0)),
            }
            for row in recent_consumption
        ],
        "attention": [
            {
                "item_id": item_id,
                "name": item["name"],
                "unit": item["unit"],
                "stock": item["stock"],
                "safe": item["safe"],
                "coverage": item["stock"] / item["safe"] * 100 if item["safe"] else None,
            }
            for item_id, item in sorted(
                ((item_id, item) for item_id, item in items if item["stock"] < item["safe"]),
                key=lambda pair: pair[1]["stock"] / pair[1]["safe"] if pair[1]["safe"] else 1,
            )[:8]
        ],
        "anomalies": [
            *(
                [
                    {
                        "key": "low-stock",
                        "label": "低於安全線",
                        "count": len(low),
                        "route": "inventory",
                        "severity": "high",
                    }
                ]
                if low
                else []
            ),
            *(
                [
                    {
                        "key": "zero-stock",
                        "label": "零庫存",
                        "count": len(zero),
                        "route": "inventory",
                        "severity": "medium",
                    }
                ]
                if zero
                else []
            ),
            *(
                [
                    {
                        "key": "shipment-delay",
                        "label": "在途延誤",
                        "count": sum(1 for row in shipment_data if row["delayed"]),
                        "route": "shipments",
                        "severity": "high",
                    }
                ]
                if any(row["delayed"] for row in shipment_data)
                else []
            ),
        ],
    }


def bootstrap_warehouse_payload(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        inventory = _rows_for_inventory(session)
        categories = (
            session.execute(
                text(
                    """
                SELECT id, name, requires_return
                FROM warehouse.item_categories
                WHERE active ORDER BY name
                """
                )
            )
            .mappings()
            .all()
        )
        warehouses = (
            session.execute(
                text(
                    """
                SELECT w.id, w.code, w.name, w.warehouse_type, w.address, w.lat, w.lng,
                       w.storage_condition, w.capacity_usage, w.active, w.created_at, w.updated_at,
                       COALESCE(SUM(l.quantity_on_hand), 0) AS stock_total
                FROM warehouse.warehouses AS w
                LEFT JOIN warehouse.stock_lots AS l
                  ON l.tenant_id = w.tenant_id AND l.warehouse_id = w.id AND l.active
                WHERE w.active
                GROUP BY w.id
                ORDER BY w.name, w.code
                """
                )
            )
            .mappings()
            .all()
        )
        hub = _warehouse_hub(session, actor, inventory)
        inbound = _inbound_rows(session)
        outbound = _outbound_rows(session)
    return {
        "INVENTORY": inventory,
        "LEDGER_CATEGORIES": [
            {"id": str(row["id"]), "name": row["name"], "requires_return": row["requires_return"]}
            for row in categories
        ],
        "WAREHOUSES": [row["name"] for row in warehouses],
        "warehouse_rows": [
            {
                **dict(row),
                "id": str(row["id"]),
                "lat": _float(row["lat"]) if row["lat"] is not None else None,
                "lng": _float(row["lng"]) if row["lng"] is not None else None,
                "capacity_usage": _float(row["capacity_usage"])
                if row["capacity_usage"] is not None
                else None,
                "stock_total": _float(row["stock_total"]),
            }
            for row in warehouses
        ],
        "INBOUND": inbound,
        "OUTBOUND": outbound,
        "SHIPMENTS": _shipment_rows(session),
        "ALERTS": [],
        "FAULT_TYPES": [],
        "WAREHOUSE_HUB": hub,
    }


def inventory_list_payload(
    actor: ActorContext,
    *,
    category: object | None = None,
) -> dict[str, object]:
    """Return canonical inventory balances for one tenant and optional category."""

    with tenant_session(actor.tenant_id) as session:
        rows = _rows_for_inventory(session)
    category_filter = str(category or "").strip().casefold()
    if category_filter:
        rows = [
            row
            for row in rows
            if category_filter
            in {
                str(row.get("categoryId") or "").casefold(),
                str(row.get("categoryCode") or "").casefold(),
                str(row.get("category") or "").casefold(),
            }
        ]
    return {
        "ok": True,
        "source": "warehouse.inventory_balance",
        "scope": "current_tenant_rls",
        "category": str(category) if category not in (None, "") else None,
        "inventory": rows,
        "items": rows,
        "count": len(rows),
        "effect_verified": True,
    }


def item_categories_payload(actor: ActorContext) -> dict[str, object]:
    """Return active canonical item categories with live item counts."""

    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT c.id, c.category_code, c.name, c.requires_return,
                           COUNT(i.id) FILTER (WHERE i.active) AS item_count
                    FROM warehouse.item_categories AS c
                    LEFT JOIN warehouse.items AS i
                      ON i.tenant_id = c.tenant_id AND i.category_id = c.id
                    WHERE c.active
                    GROUP BY c.id
                    ORDER BY c.name, c.category_code
                    """
                )
            )
            .mappings()
            .all()
        )
    categories = [
        {
            "id": str(row["id"]),
            "code": row["category_code"],
            "name": row["name"],
            "requires_return": bool(row["requires_return"]),
            "item_count": int(row["item_count"] or 0),
        }
        for row in rows
    ]
    return {
        "ok": True,
        "source": "warehouse.item_category",
        "scope": "current_tenant_rls",
        "categories": categories,
        "items": categories,
        "count": len(categories),
        "effect_verified": True,
    }


def stock_ledger_payload(
    actor: ActorContext,
    *,
    category: object,
    limit: int = 1000,
) -> dict[str, object]:
    """Return the canonical stock movement ledger for one category."""

    category_filter = str(category or "").strip()
    if not category_filter:
        raise HTTPException(status_code=422, detail="category must not be empty")
    bounded_limit = max(1, min(int(limit), 2000))
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT l.id, l.occurred_at, l.movement_type, l.quantity_delta,
                           l.source_type, l.source_id,
                           i.id AS item_id, i.item_code, i.name AS item_name, i.unit,
                           c.id AS category_id, c.category_code, c.name AS category_name,
                           w.id AS warehouse_id, w.code AS warehouse_code,
                           w.name AS warehouse_name,
                           loc.id AS location_id, loc.location_code
                    FROM warehouse.stock_ledger AS l
                    JOIN warehouse.items AS i
                      ON i.tenant_id = l.tenant_id AND i.id = l.item_id
                    LEFT JOIN warehouse.item_categories AS c
                      ON c.tenant_id = i.tenant_id AND c.id = i.category_id
                    LEFT JOIN warehouse.warehouses AS w
                      ON w.tenant_id = l.tenant_id AND w.id = l.warehouse_id
                    LEFT JOIN warehouse.warehouse_locations AS loc
                      ON loc.tenant_id = l.tenant_id AND loc.id = l.location_id
                    WHERE lower(COALESCE(c.category_code, '')) = lower(:category)
                       OR lower(COALESCE(c.name, '')) = lower(:category)
                       OR CAST(c.id AS text) = :category
                    ORDER BY l.occurred_at DESC, l.id DESC
                    LIMIT :limit
                    """
                ),
                {"category": category_filter, "limit": bounded_limit},
            )
            .mappings()
            .all()
        )
    entries = [
        {
            **dict(row),
            "id": str(row["id"]),
            "source_id": str(row["source_id"]) if row["source_id"] else None,
            "item_id": str(row["item_id"]),
            "category_id": str(row["category_id"]) if row["category_id"] else None,
            "warehouse_id": str(row["warehouse_id"]) if row["warehouse_id"] else None,
            "location_id": str(row["location_id"]) if row["location_id"] else None,
            "quantity_delta": _float(row["quantity_delta"]),
            "occurred_at": _iso(row["occurred_at"]),
        }
        for row in rows
    ]
    return {
        "ok": True,
        "source": "warehouse.stock_ledger",
        "scope": "current_tenant_rls",
        "category": category_filter,
        "ledger": entries,
        "entries": entries,
        "items": entries,
        "count": len(entries),
        "effect_verified": True,
    }


def inventory_batches(actor: ActorContext, item_id: str) -> dict[str, object]:
    try:
        item_uuid = UUID(item_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid item id"
        ) from exc
    with tenant_session(actor.tenant_id) as session:
        item = (
            session.execute(
                text(
                    """
                SELECT unit, required_storage_condition, default_shelf_life_days
                FROM warehouse.items WHERE id = :item_id AND active
                """
                ),
                {"item_id": item_uuid},
            )
            .mappings()
            .one_or_none()
        )
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        rows = (
            session.execute(
                text(
                    """
                SELECT l.id, l.batch_no, l.production_date, l.expires_at, l.quantity_on_hand,
                       l.cold_chain_ok, w.name AS warehouse, loc.location_code AS location,
                       ROW_NUMBER() OVER (
                         ORDER BY l.expires_at NULLS LAST, l.created_at, l.id
                       ) AS fefo_rank
                FROM warehouse.stock_lots AS l
                JOIN warehouse.warehouses AS w
                  ON w.tenant_id = l.tenant_id AND w.id = l.warehouse_id
                LEFT JOIN warehouse.warehouse_locations AS loc
                  ON loc.tenant_id = l.tenant_id AND loc.id = l.location_id
                WHERE l.item_id = :item_id AND l.active AND l.quantity_on_hand > 0
                ORDER BY l.expires_at NULLS LAST, l.created_at, l.id
                """
                ),
                {"item_id": item_uuid},
            )
            .mappings()
            .all()
        )
    today = date.today()
    return {
        "unit": item["unit"],
        "requiredCondition": item["required_storage_condition"],
        "shelfLife": item["default_shelf_life_days"],
        "batches": [
            {
                "id": str(row["id"]),
                "batchNo": row["batch_no"] or "—",
                "productionDate": _iso(row["production_date"]),
                "expireAt": _iso(row["expires_at"]),
                "days": (row["expires_at"] - today).days if row["expires_at"] else None,
                "qty": _float(row["quantity_on_hand"]),
                "coldOk": row["cold_chain_ok"],
                "warehouse": row["warehouse"],
                "location": row["location"] or "—",
                "fefoRank": int(row["fefo_rank"]),
            }
            for row in rows
        ],
    }


def create_item(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    """Create tenant item master data used by every native stock operation."""
    _require(actor, "settings.manage")
    name = str(payload.get("item_name") or payload.get("name") or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Item name is required"
        )
    if len(name) > 256:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Item name is too long",
        )
    unit = str(payload.get("unit") or "件").strip() or "件"
    model = str(payload.get("spec_model") or payload.get("spec") or "").strip() or None
    with tenant_session(actor.tenant_id) as session:
        existing = session.execute(
            text("SELECT id FROM warehouse.items WHERE lower(name) = lower(:name) AND active"),
            {"name": name},
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active item with this name already exists",
            )
        category = _item_category(
            session, payload.get("category_id") or payload.get("category")
        )
        item_id = uuid4()
        item_code = f"ITEM-{item_id.hex[:10].upper()}"
        session.execute(
            text(
                """
                INSERT INTO warehouse.items(
                  id, tenant_id, category_id, item_code, name, model, unit
                ) VALUES (
                  :id, :tenant_id, :category_id, :item_code, :name, :model, :unit
                )
                """
            ),
            {
                "id": item_id,
                "tenant_id": actor.tenant_id,
                "category_id": category["id"] if category else None,
                "item_code": item_code,
                "name": name,
                "model": model,
                "unit": unit,
            },
        )
        _audit(
            session,
            actor,
            "warehouse.item.created",
            {"item_id": str(item_id), "item_code": item_code, "name": name},
        )
    return {
        "ok": True,
        "item": {
            "id": str(item_id),
            "code": item_code,
            "name": name,
            "model": model,
            "unit": unit,
            "category_id": str(category["id"]) if category else None,
            "category": category["name"] if category else None,
        },
    }


def update_item(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    """Update the native item master while preserving stock and ledger identity."""
    _require(actor, "inventory.adjust", "settings.manage")
    with tenant_session(actor.tenant_id) as session:
        item = _item_for_edit(
            session, item_id=payload.get("id"), name=payload.get("name")
        )
        new_name = str(payload.get("new_name") or item["name"]).strip()
        unit = str(payload.get("unit") or item["unit"]).strip()
        model_value = payload.get("spec")
        model = item["model"] if model_value is None else str(model_value).strip() or None
        price_value = payload.get("price")
        if price_value is None:
            unit_price = item["unit_price"]
        else:
            try:
                unit_price = Decimal(str(price_value))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="price must be a non-negative number",
                ) from exc
            if not unit_price.is_finite() or unit_price < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="price must be a non-negative number",
                )
        category_value = payload.get("category")
        category = (
            _item_category(session, category_value)
            if category_value is not None
            else {"id": item["category_id"]}
        )
        session.execute(
            text(
                """
                UPDATE warehouse.items
                SET name = :name,
                    model = :model,
                    unit = :unit,
                    unit_price = :unit_price,
                    category_id = :category_id,
                    updated_at = now()
                WHERE id = :item_id
                """
            ),
            {
                "item_id": item["id"],
                "name": new_name,
                "model": model,
                "unit": unit,
                "unit_price": unit_price,
                "category_id": category["id"],
            },
        )
        _audit(
            session,
            actor,
            "warehouse.item.updated",
            {"item_id": str(item["id"]), "name": new_name},
        )
    return {
        "ok": True,
        "item": {
            "id": str(item["id"]),
            "code": item["item_code"],
            "name": new_name,
            "model": model,
            "unit": unit,
            "unit_price": float(unit_price) if unit_price is not None else None,
            "category_id": str(category["id"]) if category["id"] else None,
        },
    }


def archive_item(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    """Archive item master data only when no stock remains."""
    _require(actor, "inventory.adjust")
    with tenant_session(actor.tenant_id) as session:
        item = _item_for_edit(
            session, item_id=payload.get("id"), name=payload.get("name")
        )
        stock = session.execute(
            text(
                """
                SELECT COALESCE(SUM(quantity_on_hand), 0)
                FROM warehouse.stock_lots
                WHERE item_id = :item_id AND active
                """
            ),
            {"item_id": item["id"]},
        ).scalar_one()
        if Decimal(str(stock)) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Item still has stock and cannot be archived",
            )
        session.execute(
            text("UPDATE warehouse.items SET active = false, updated_at = now() WHERE id = :id"),
            {"id": item["id"]},
        )
        _audit(
            session,
            actor,
            "warehouse.item.archived",
            {"item_id": str(item["id"]), "name": item["name"]},
        )
    return {"ok": True, "archived": True, "item_id": str(item["id"])}


def create_inbound(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "inventory.inbound")
    request_id = str(payload.get("request_id") or "").strip() or None
    lines = payload.get("lines")
    if not isinstance(lines, list) or not lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one line is required"
        )
    with tenant_session(actor.tenant_id) as session:
        if request_id:
            existing = (
                session.execute(
                    text(
                        "SELECT order_no FROM warehouse.inbound_orders "
                        "WHERE client_request_id = :request_id"
                    ),
                    {"request_id": request_id},
                )
                .mappings()
                .one_or_none()
            )
            if existing:
                return {"ok": True, "existing": True, "order_no": existing["order_no"]}
        warehouse = _warehouse(
            session,
            str(payload.get("warehouse") or ""),
            default_if_missing=True,
        )
        order_id = uuid4()
        order_no = _new_no("IN")
        session.execute(
            text(
                """
                INSERT INTO warehouse.inbound_orders(
                  id, tenant_id, order_no, inbound_type, source_name, warehouse_id,
                  status, client_request_id, created_by
                ) VALUES (
                  :id, :tenant_id, :order_no, :inbound_type, :source_name, :warehouse_id,
                  'received', :client_request_id, :created_by
                )
                """
            ),
            {
                "id": order_id,
                "tenant_id": actor.tenant_id,
                "order_no": order_no,
                "inbound_type": str(payload.get("type") or "入庫"),
                "source_name": str(payload.get("source") or "").strip() or None,
                "warehouse_id": warehouse["id"],
                "client_request_id": request_id,
                "created_by": actor.user_id,
            },
        )
        for index, raw_line in enumerate(lines, start=1):
            if not isinstance(raw_line, dict):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid inbound line"
                )
            item = _item(session, str(raw_line.get("name") or ""))
            quantity = _decimal(raw_line.get("qty"))
            production_date = raw_line.get("production_date") or None
            try:
                production_day = (
                    date.fromisoformat(str(production_date)) if production_date else None
                )
                explicit_expiry = raw_line.get("expire_at") or None
                expires_at = (
                    date.fromisoformat(str(explicit_expiry)) if explicit_expiry else None
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="production_date and expire_at must use YYYY-MM-DD",
                ) from exc
            shelf_life_days = raw_line.get("shelf_life_days")
            if expires_at is None and production_day:
                shelf_days = (
                    int(shelf_life_days)
                    if shelf_life_days is not None
                    else item["default_shelf_life_days"]
                )
                if shelf_days:
                    expires_at = production_day + timedelta(days=int(shelf_days))
            lot_id = uuid4()
            batch_no = str(
                raw_line.get("batch_no")
                or raw_line.get("batch")
                or f"{order_no}-{index:02d}"
            )
            session.execute(
                text(
                    """
                    INSERT INTO warehouse.stock_lots(
                      id, tenant_id, item_id, warehouse_id, batch_no, production_date,
                      expires_at, quantity_on_hand, quality_status
                    ) VALUES (
                      :id, :tenant_id, :item_id, :warehouse_id, :batch_no, :production_date,
                      :expires_at, :quantity, 'qualified'
                    )
                    """
                ),
                {
                    "id": lot_id,
                    "tenant_id": actor.tenant_id,
                    "item_id": item["id"],
                    "warehouse_id": warehouse["id"],
                    "batch_no": batch_no,
                    "production_date": production_day,
                    "expires_at": expires_at,
                    "quantity": quantity,
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO warehouse.inbound_order_lines(
                      id, tenant_id, inbound_order_id, item_id, lot_id, quantity,
                      unit_cost, batch_no, production_date, expires_at
                    ) VALUES (
                      :id, :tenant_id, :inbound_order_id, :item_id, :lot_id, :quantity,
                      :unit_cost, :batch_no, :production_date, :expires_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "inbound_order_id": order_id,
                    "item_id": item["id"],
                    "lot_id": lot_id,
                    "quantity": quantity,
                    "unit_cost": item["unit_price"],
                    "batch_no": batch_no,
                    "production_date": production_day,
                    "expires_at": expires_at,
                },
            )
            _insert_ledger(
                session,
                actor=actor,
                item_id=item["id"],
                lot_id=lot_id,
                warehouse_id=warehouse["id"],
                movement_type="inbound",
                quantity_delta=quantity,
                source_type="inbound_order",
                source_id=order_id,
            )
        _audit(session, actor, "warehouse.inbound.created", {"order_no": order_no})
    return {"ok": True, "order_no": order_no, "message": f"Inbound {order_no} received"}


def create_outbound(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "inventory.outbound")
    request_id = str(payload.get("request_id") or "").strip() or None
    lines = payload.get("lines")
    if not isinstance(lines, list) or not lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one line is required"
        )
    with tenant_session(actor.tenant_id) as session:
        if request_id:
            existing = (
                session.execute(
                    text(
                        "SELECT order_no FROM warehouse.outbound_orders "
                        "WHERE client_request_id = :request_id"
                    ),
                    {"request_id": request_id},
                )
                .mappings()
                .one_or_none()
            )
            if existing:
                return {"ok": True, "existing": True, "order_no": existing["order_no"]}
        order_id = uuid4()
        order_no = _new_no("OUT")
        use_type = str(payload.get("use") or "領用")
        urgent = use_type == "搶修" or bool(payload.get("urgent"))
        session.execute(
            text(
                """
                INSERT INTO warehouse.outbound_orders(
                  id, tenant_id, order_no, use_type, department_name, target_name,
                  urgent, status, client_request_id, created_by
                ) VALUES (
                  :id, :tenant_id, :order_no, :use_type, :department_name, :target_name,
                  :urgent, 'issued', :client_request_id, :created_by
                )
                """
            ),
            {
                "id": order_id,
                "tenant_id": actor.tenant_id,
                "order_no": order_no,
                "use_type": use_type,
                "department_name": str(payload.get("dept") or "").strip() or None,
                "target_name": str(payload.get("target") or "").strip() or None,
                "urgent": urgent,
                "client_request_id": request_id,
                "created_by": actor.user_id,
            },
        )
        for raw_line in lines:
            if not isinstance(raw_line, dict):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid outbound line"
                )
            item = _item(session, str(raw_line.get("name") or ""))
            quantity = _decimal(raw_line.get("qty"))
            consumed = _consume_lots(session, item_id=item["id"], quantity=quantity)
            line_id = uuid4()
            source_warehouse_id = consumed[0][0]["warehouse_id"]
            session.execute(
                text(
                    """
                    INSERT INTO warehouse.outbound_order_lines(
                      id, tenant_id, outbound_order_id, item_id, quantity,
                      unit_cost, source_warehouse_id
                    ) VALUES (
                      :id, :tenant_id, :outbound_order_id, :item_id, :quantity,
                      :unit_cost, :source_warehouse_id
                    )
                    """
                ),
                {
                    "id": line_id,
                    "tenant_id": actor.tenant_id,
                    "outbound_order_id": order_id,
                    "item_id": item["id"],
                    "quantity": quantity,
                    "unit_cost": item["unit_price"],
                    "source_warehouse_id": source_warehouse_id,
                },
            )
            for lot, taken in consumed:
                _insert_ledger(
                    session,
                    actor=actor,
                    item_id=item["id"],
                    lot_id=lot["id"],
                    warehouse_id=lot["warehouse_id"],
                    movement_type="outbound",
                    quantity_delta=-taken,
                    source_type="outbound_order",
                    source_id=order_id,
                )
            if use_type == "借用":
                session.execute(
                    text(
                        """
                        INSERT INTO warehouse.loan_returns(
                          id, tenant_id, outbound_line_id, expected_return_at
                        ) VALUES (:id, :tenant_id, :outbound_line_id, :expected_return_at)
                        """
                    ),
                    {
                        "id": uuid4(),
                        "tenant_id": actor.tenant_id,
                        "outbound_line_id": line_id,
                        "expected_return_at": datetime.now(UTC) + timedelta(days=14),
                    },
                )
        _audit(
            session, actor, "warehouse.outbound.created", {"order_no": order_no, "urgent": urgent}
        )
    return {"ok": True, "order_no": order_no, "message": f"Outbound {order_no} issued"}


def create_replenishment(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "inventory.adjust", "inventory.read")
    with tenant_session(actor.tenant_id) as session:
        item = _item(session, str(payload.get("item_name") or ""))
        quantity = _decimal(payload.get("need"), field="need")
        request_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO warehouse.replenishment_requests(
                  id, tenant_id, item_id, requested_quantity, requested_by
                ) VALUES (:id, :tenant_id, :item_id, :requested_quantity, :requested_by)
                """
            ),
            {
                "id": request_id,
                "tenant_id": actor.tenant_id,
                "item_id": item["id"],
                "requested_quantity": quantity,
                "requested_by": actor.user_id,
            },
        )
        _audit(
            session,
            actor,
            "warehouse.replenishment.requested",
            {"item": item["name"], "need": str(quantity)},
        )
    return {"ok": True, "request_id": str(request_id), "status": "pending"}


def dispatch_shipment(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "inventory.shipment")
    with tenant_session(actor.tenant_id) as session:
        item = _item(session, str(payload.get("item") or ""))
        quantity = _decimal(payload.get("qty"))
        destination = _warehouse(session, str(payload.get("to") or ""))
        source = _warehouse(session, str(payload.get("from") or ""), required=False)
        if source is None:
            candidate = (
                session.execute(
                    text(
                        """
                    SELECT w.id, w.code, w.name
                    FROM warehouse.stock_lots AS l
                    JOIN warehouse.warehouses AS w
                      ON w.tenant_id = l.tenant_id AND w.id = l.warehouse_id
                    WHERE l.item_id = :item_id AND l.active AND l.quantity_on_hand > 0
                    GROUP BY w.id ORDER BY SUM(l.quantity_on_hand) DESC, w.name LIMIT 1
                    """
                    ),
                    {"item_id": item["id"]},
                )
                .mappings()
                .one_or_none()
            )
            if candidate is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No source warehouse has available stock",
                )
            source = dict(candidate)
        if source["id"] == destination["id"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Source and destination must differ",
            )
        consumed = _consume_lots(
            session, item_id=item["id"], quantity=quantity, warehouse_id=source["id"]
        )
        shipment_id = uuid4()
        shipment_no = _new_no("SHP")
        batch_no = consumed[0][0]["batch_no"] if len(consumed) == 1 else "MIXED"
        expiry_dates = [lot["expires_at"] for lot, _ in consumed if lot["expires_at"]]
        session.execute(
            text(
                """
                INSERT INTO warehouse.shipments(
                  id, tenant_id, shipment_no, item_id, source_warehouse_id,
                  destination_warehouse_id,
                  quantity, batch_no, expires_at, eta_at, created_by
                ) VALUES (
                  :id, :tenant_id, :shipment_no, :item_id, :source_warehouse_id,
                  :destination_warehouse_id,
                  :quantity, :batch_no, :expires_at, :eta_at, :created_by
                )
                """
            ),
            {
                "id": shipment_id,
                "tenant_id": actor.tenant_id,
                "shipment_no": shipment_no,
                "item_id": item["id"],
                "source_warehouse_id": source["id"],
                "destination_warehouse_id": destination["id"],
                "quantity": quantity,
                "batch_no": batch_no,
                "expires_at": min(expiry_dates) if expiry_dates else None,
                "eta_at": datetime.now(UTC) + timedelta(hours=2),
                "created_by": actor.user_id,
            },
        )
        for lot, taken in consumed:
            _insert_ledger(
                session,
                actor=actor,
                item_id=item["id"],
                lot_id=lot["id"],
                warehouse_id=source["id"],
                movement_type="transfer_out",
                quantity_delta=-taken,
                source_type="shipment",
                source_id=shipment_id,
            )
        _audit(session, actor, "warehouse.shipment.dispatched", {"shipment_no": shipment_no})
    return {"ok": True, "shipment_no": shipment_no, "message": f"Dispatched {shipment_no}"}


def _shipment_action(actor: ActorContext, shipment_no: str, action: str) -> dict[str, object]:
    _require(actor, "inventory.shipment")
    with tenant_session(actor.tenant_id) as session:
        shipment = (
            session.execute(
                text(
                    "SELECT * FROM warehouse.shipments WHERE shipment_no = :shipment_no FOR UPDATE"
                ),
                {"shipment_no": shipment_no},
            )
            .mappings()
            .one_or_none()
        )
        if shipment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
        if shipment["status"] != "in_transit":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Shipment is no longer in transit"
            )
        now = datetime.now(UTC)
        if action == "arrive":
            new_lot_id = uuid4()
            session.execute(
                text(
                    """
                    INSERT INTO warehouse.stock_lots(
                      id, tenant_id, item_id, warehouse_id, batch_no, expires_at, quantity_on_hand
                    ) VALUES (
                      :id, :tenant_id, :item_id, :warehouse_id, :batch_no, :expires_at, :quantity
                    )
                    """
                ),
                {
                    "id": new_lot_id,
                    "tenant_id": actor.tenant_id,
                    "item_id": shipment["item_id"],
                    "warehouse_id": shipment["destination_warehouse_id"],
                    "batch_no": shipment["batch_no"],
                    "expires_at": shipment["expires_at"],
                    "quantity": shipment["quantity"],
                },
            )
            session.execute(
                text(
                    "UPDATE warehouse.shipments SET status = 'arrived', "
                    "arrived_at = :now WHERE id = :id"
                ),
                {"now": now, "id": shipment["id"]},
            )
            _insert_ledger(
                session,
                actor=actor,
                item_id=shipment["item_id"],
                lot_id=new_lot_id,
                warehouse_id=shipment["destination_warehouse_id"],
                movement_type="transfer_in",
                quantity_delta=Decimal(str(shipment["quantity"])),
                source_type="shipment",
                source_id=shipment["id"],
            )
        else:
            restore_lot_id = uuid4()
            session.execute(
                text(
                    """
                    INSERT INTO warehouse.stock_lots(
                      id, tenant_id, item_id, warehouse_id, batch_no, expires_at, quantity_on_hand
                    ) VALUES (
                      :id, :tenant_id, :item_id, :warehouse_id, :batch_no, :expires_at, :quantity
                    )
                    """
                ),
                {
                    "id": restore_lot_id,
                    "tenant_id": actor.tenant_id,
                    "item_id": shipment["item_id"],
                    "warehouse_id": shipment["source_warehouse_id"],
                    "batch_no": shipment["batch_no"],
                    "expires_at": shipment["expires_at"],
                    "quantity": shipment["quantity"],
                },
            )
            session.execute(
                text(
                    "UPDATE warehouse.shipments SET status = 'cancelled', "
                    "cancelled_at = :now WHERE id = :id"
                ),
                {"now": now, "id": shipment["id"]},
            )
            _insert_ledger(
                session,
                actor=actor,
                item_id=shipment["item_id"],
                lot_id=restore_lot_id,
                warehouse_id=shipment["source_warehouse_id"],
                movement_type="transfer_in",
                quantity_delta=Decimal(str(shipment["quantity"])),
                source_type="shipment_cancel",
                source_id=shipment["id"],
            )
        _audit(session, actor, f"warehouse.shipment.{action}d", {"shipment_no": shipment_no})
    return {
        "ok": True,
        "shipment_no": shipment_no,
        "status": "arrived" if action == "arrive" else "cancelled",
    }


def arrive_shipment(actor: ActorContext, shipment_no: str) -> dict[str, object]:
    return _shipment_action(actor, shipment_no, "arrive")


def cancel_shipment(actor: ActorContext, shipment_no: str) -> dict[str, object]:
    return _shipment_action(actor, shipment_no, "cancel")


def alerts_by_item(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _rows_for_inventory(session)
    grouped: dict[str, dict[str, float]] = defaultdict(lambda: {"stock": 0.0, "safe": 0.0})
    for row in rows:
        grouped[row["itemId"]]["stock"] += _float(row["stock"])
        grouped[row["itemId"]]["safe"] += _float(row["safe"])
    return {
        "byItem": {
            key: {"count": 1, "level": "red" if data["stock"] <= 0 else "orange"}
            for key, data in grouped.items()
            if data["stock"] < data["safe"]
        }
    }


def pending_returns(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT r.id AS reminder_id, o.order_no AS transaction_no, i.name AS item_name,
                       c.name AS category_name, l.quantity, i.unit, o.target_name AS work_location,
                       o.use_type AS purpose, r.expected_return_at,
                       CASE WHEN r.expected_return_at < now() THEN 'overdue'
                            ELSE r.reminder_status END AS reminder_status
                FROM warehouse.loan_returns AS r
                JOIN warehouse.outbound_order_lines AS l
                  ON l.tenant_id = r.tenant_id AND l.id = r.outbound_line_id
                JOIN warehouse.outbound_orders AS o
                  ON o.tenant_id = l.tenant_id AND o.id = l.outbound_order_id
                JOIN warehouse.items AS i ON i.tenant_id = l.tenant_id AND i.id = l.item_id
                LEFT JOIN warehouse.item_categories AS c
                  ON c.tenant_id = i.tenant_id AND c.id = i.category_id
                WHERE r.returned_at IS NULL
                ORDER BY r.expected_return_at
                """
                )
            )
            .mappings()
            .all()
        )
    return {
        "rows": [
            {
                **dict(row),
                "reminder_id": str(row["reminder_id"]),
                "quantity": _float(row["quantity"]),
                "expected_return_at": _iso(row["expected_return_at"]),
            }
            for row in rows
        ]
    }


def reports_summary(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        inventory = _rows_for_inventory(session)
        hub = _warehouse_hub(session, actor, inventory)
    return {
        "kpis": [{"key": "庫存總儲值", "value": hub["inventory"]["stock_value"], "unit": ""}],
        "turnover": None,
        "trend": {"labels": [], "inbound": [], "outbound": [], "urgent": []},
        "value_dist": [
            {"label": row["label"], "value": row["value"]} for row in hub["category_mix"]
        ],
        "top_consume": [
            {"name": row["name"], "value": row["quantity"]} for row in hub["consumption"]
        ],
        "alert_stats": {
            "handled": 0,
            "total": 0,
            "pending_returns": len(pending_returns(actor)["rows"]),
        },
    }


def gis_overview(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        zones = (
            session.execute(
                text(
                    """
                SELECT id AS zone_id, warehouse_id, zone_code, zone_name, zone_type,
                       floor_no, capacity_usage, rack_count, item_count, alert_count, color
                FROM warehouse.warehouse_zones WHERE active ORDER BY zone_name, zone_code
                """
                )
            )
            .mappings()
            .all()
        )
        locations = (
            session.execute(
                text(
                    """
                SELECT id, warehouse_id, zone_id, location_code, rack_code, floor_no,
                       capacity_usage, capacity_limit, alert_status
                FROM warehouse.warehouse_locations WHERE active ORDER BY location_code
                """
                )
            )
            .mappings()
            .all()
        )
    return {
        "zones": [
            {
                **dict(row),
                "zone_id": str(row["zone_id"]),
                "warehouse_id": str(row["warehouse_id"]),
                "capacity_usage": _float(row["capacity_usage"])
                if row["capacity_usage"] is not None
                else None,
            }
            for row in zones
        ],
        "locations": [
            {
                **dict(row),
                "id": str(row["id"]),
                "warehouse_id": str(row["warehouse_id"]),
                "zone_id": str(row["zone_id"]) if row["zone_id"] else None,
                "capacity_usage": _float(row["capacity_usage"])
                if row["capacity_usage"] is not None
                else None,
                "capacity_limit": _float(row["capacity_limit"])
                if row["capacity_limit"] is not None
                else None,
            }
            for row in locations
        ],
    }
