"""Top products by stock decoupled for CNC AMR architecture."""

from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.warehouse.dashboard.dashboard_schema import (
    ReportTopProductsResponse,
    TopProductRow,
)
from app.modules.warehouse.dashboard.dashboard_snapshot_service import (
    _storage_stock_filters,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_service import _ensure_warehouse_exists

VN_TIMEZONE = "Asia/Ho_Chi_Minh"
TOP_LIMIT = 5


def _rows_to_top_product(rows) -> list[TopProductRow]:
    result: list[TopProductRow] = []
    for row in rows:
        item_id = row[0]
        sku = row[1]
        name = row[2]
        qty = int(row[3] or 0)
        label = f"{sku} - {name}" if name else sku
        result.append(
            TopProductRow(
                item_id=item_id,
                label=label,
                total_quantity=qty,
            )
        )
    return result


def _top_stock(db: Session, *, warehouse_id: int) -> list[TopProductRow]:
    total_qty = func.sum(ItemStock.quantity).label("total_qty")
    rows = (
        db.query(
            Item.id.label("item_id"),
            Item.sku,
            Item.name,
            total_qty,
        )
        .join(ItemStock, ItemStock.item_id == Item.id)
        .join(Location, Location.id == ItemStock.location_id)
        .filter(*_storage_stock_filters(warehouse_id))
        .group_by(Item.id, Item.sku, Item.name)
        .order_by(total_qty.desc())
        .limit(TOP_LIMIT)
        .all()
    )
    return _rows_to_top_product(rows)


def get_report_top_products(
    db: Session,
    *,
    warehouse_id: int,
    period: Literal["week", "month"],
) -> ReportTopProductsResponse:
    _ensure_warehouse_exists(db, warehouse_id)
    return ReportTopProductsResponse(
        period=period,
        inbound_top=[],
        outbound_top=[],
        stock_top=_top_stock(db, warehouse_id=warehouse_id),
    )
