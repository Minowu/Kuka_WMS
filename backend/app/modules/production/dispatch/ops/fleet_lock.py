"""Auto-split from dispatch_core — keep behavior identical."""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from sqlalchemy.orm import Session

from app.core.logger import bind_context, get_logger, log_context
from app.modules.production.production_models import (
    FleetTask,
    Machine,
    ProductionRecord,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportQueue,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.dispatch")


def lock_cart_and_dispatch_fleet_task(
    core,
    db: Session,
    transport_req: TransportRequest,
    cart: ItemStock,
    pickup_location_id: int,
    dropoff_location_id: int,
) -> FleetTask:
    """Atomically lock container and create FleetTask (Tx1) then dispatch submitMission (Tx2)."""
    mission_code = f"MS{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
    fleet_req_id = f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"

    dropoff_loc = db.query(Location).filter(Location.id == dropoff_location_id).first()
    station_code = dropoff_loc.location_code if dropoff_loc else str(dropoff_location_id)
    machine_code = dropoff_loc.machine.machine_code if dropoff_loc and getattr(dropoff_loc, "machine", None) else None

    cart.is_locked = True
    cart.locked_by_mission_code = mission_code
    cart.destination_location_id = dropoff_location_id

    prev_req_status = transport_req.status or "new"
    transport_req.container_id = cart.id
    transport_req.source_location_id = pickup_location_id
    transport_req.destination_location_id = dropoff_location_id
    transport_req.status = "in_progress"

    fleet_task = FleetTask(
        mission_code=mission_code,
        fleet_request_id=fleet_req_id,
        transport_request_id=transport_req.id,
        pickup_location_id=pickup_location_id,
        dropoff_location_id=dropoff_location_id,
        container_id=cart.id,
        container_code=cart.container_code,
        status="pending_submit",
    )
    db.add(fleet_task)
    loc_ids = sorted({int(lid) for lid in (pickup_location_id, dropoff_location_id) if lid is not None})
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[transport_req.created_by],
    )
    db.commit()
    db.refresh(fleet_task)

    # Bind context
    bind_context(
        transport_request_id=transport_req.id,
        fleet_task_id=fleet_task.id,
        container_code=cart.container_code,
        station_code=station_code,
        machine_code=machine_code,
    )

    logger.info(
        "TransportRequest %s: %s -> %s (reason: %s)",
        transport_req.id,
        prev_req_status,
        "in_progress",
        f"Assigned cart {cart.container_code} and created FleetTask {mission_code}",
    )
    logger.info(
        "FleetTask %s: %s -> %s (reason: %s)",
        fleet_task.mission_code,
        "new",
        "pending_submit",
        f"Created task for TransportRequest {transport_req.id} (cart {cart.container_code})",
    )
    logger.info(
        "dispatch_transport_request: transport_request_id=%s, cart=%s, pickup=%s, dropoff=%s (%s), mission=%s",
        transport_req.id,
        cart.container_code,
        pickup_location_id,
        dropoff_location_id,
        station_code,
        mission_code,
    )

    from app.modules.production.production_celery_task import enqueue_fleet_submit
    enqueue_fleet_submit(fleet_task.id)

    publish_event(
        "floor.changed",
        {
            "reason": "task_dispatched",
            "mission_code": mission_code,
            "location_ids": loc_ids,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    return fleet_task
