from datetime import datetime, time
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.warehouse.dashboard.dashboard_schema import ReportKpiResponse
from app.modules.warehouse.item import item_service
from app.modules.warehouse.notificcation import notification_service
from app.modules.warehouse.warehouse_zone.warehouse_service import _ensure_warehouse_exists
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.production.production_models import FleetTask, TransportQueue, ProductionRecord


def get_report_kpis(db: Session, *, warehouse_id: int) -> ReportKpiResponse:
    _ensure_warehouse_exists(db, warehouse_id)

    # Active WIP carts
    active_carts_count = (
        db.query(func.count(ItemStock.id))
        .join(Location, Location.id == ItemStock.location_id)
        .filter(
            Location.warehouse_id == warehouse_id,
            ItemStock.is_active.is_(True),
            ItemStock.quantity > 0,
        )
        .scalar()
        or 0
    )

    # In-transit AMR tasks
    in_transit_amr_count = (
        db.query(func.count(FleetTask.id))
        .filter(FleetTask.status.in_(["pending", "dispatched", "navigating", "in_progress"]))
        .scalar()
        or 0
    )

    # Queued transport requests waiting for available carts or wash stations
    queued_requests_count = (
        db.query(func.count(TransportQueue.id))
        .filter(TransportQueue.status == "pending")
        .scalar()
        or 0
    )

    # Production records completed today
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    parts_completed_today = (
        db.query(func.count(ProductionRecord.id))
        .filter(ProductionRecord.completed_at >= today_start)
        .scalar()
        or 0
    )

    # Total inventory / WIP value
    try:
        inv_value = item_service.compute_total_inventory_value(db, warehouse_id)
    except Exception:
        inv_value = Decimal(0)

    return ReportKpiResponse(
        total_inbound_orders=0,
        total_outbound_orders=0,
        total_inventory_value=inv_value,
        unsolved_notifications=notification_service.count_unsolved_notifications(
            db, warehouse_id
        ),
        active_carts_count=active_carts_count,
        in_transit_amr_count=in_transit_amr_count,
        queued_requests_count=queued_requests_count,
        parts_completed_today=parts_completed_today,
    )
