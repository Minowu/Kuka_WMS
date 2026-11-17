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


def complete_washing_and_return_empty_cart_impl(
    core,
    db: Session,
    container_code: str,
    operator_id: Optional[int] = None,
) -> TransportRequest:
    """Empty cart return from Washing Station to EMPTY_CART_BUFFER."""
    clean_code = container_code.strip()
    cart = (
        db.query(ItemStock)
        .filter(ItemStock.container_code == clean_code, ItemStock.is_active.is_(True))
        .first()
    )
    if not cart:
        raise ValueError(f"Không tìm thấy khay/xe '{clean_code}' đang hoạt động tại khu Tẩy rửa.")

    if cart.is_locked:
        raise ValueError(f"Xe '{clean_code}' đang bị khóa bởi nhiệm vụ '{cart.locked_by_mission_code}'.")

    loc = db.query(Location).filter(Location.id == cart.location_id).first()
    if not loc or loc.location_type != "WASHING_SLOT":
        raise ValueError(f"Xe '{clean_code}' không nằm tại vị trí Khu Tẩy Rửa (WASHING_SLOT).")

    station_code = loc.location_code if loc else None
    bind_context(container_code=clean_code, station_code=station_code)
    logger.info(
        "call_empty_cart_async input: container_code=%s, location=%s, operator_id=%s",
        clean_code,
        station_code,
        operator_id,
    )

    buffer_slot = core.selector.find_next_empty_buffer_slot(db)
    req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"

    if buffer_slot:
        logger.info(
            "call_empty_cart_async candidate decision: selected empty buffer slot %s for cart %s",
            buffer_slot.location_code,
            clean_code,
        )
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="RETURN_EMPTY_CART",
            item_id=cart.item_id,
            source_location_id=cart.location_id,
            destination_location_id=buffer_slot.id,
            container_id=cart.id,
            required_stage_level=0,
            status="pending",
            priority=15,
            created_by=operator_id,
        )
        db.add(transport_req)
        db.flush()

        bind_context(transport_request_id=transport_req.id)
        logger.info(
            "TransportRequest %s: %s -> %s (reason: %s)",
            transport_req.id,
            "new",
            "pending",
            f"Returning empty cart {clean_code} to buffer slot {buffer_slot.location_code}",
        )

        cart.quantity = 0
        cart.status = "empty"
        cart.current_stage_level = 0
        db.flush()

        try:
            core.lock_cart_and_dispatch_fleet_task(
                db=db,
                transport_req=transport_req,
                cart=cart,
                pickup_location_id=cart.location_id,
                dropoff_location_id=buffer_slot.id,
            )
        except Exception:
            cart.status = "available"
            db.commit()
            raise
    else:
        logger.info(
            "call_empty_cart_async candidate decision: no empty buffer slot available for cart %s; queuing request",
            clean_code,
        )
        cart.quantity = 0
        cart.status = "empty"
        cart.current_stage_level = 0
        db.flush()
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="RETURN_EMPTY_CART",
            item_id=cart.item_id,
            source_location_id=cart.location_id,
            destination_location_id=cart.location_id,
            container_id=cart.id,
            required_stage_level=0,
            status="queued_for_slot",
            priority=15,
            created_by=operator_id,
        )
        db.add(transport_req)
        db.flush()

        bind_context(transport_request_id=transport_req.id)
        logger.info(
            "TransportRequest %s: %s -> %s (reason: %s)",
            transport_req.id,
            "new",
            "queued_for_slot",
            f"No empty buffer slot available for cart {clean_code}, enqueued in WAITING_SLOT",
        )
        core.queue_service.enqueue(
            db=db,
            request_id=transport_req.id,
            queue_type="WAITING_SLOT",
            target_stage_level=0,
            priority=15,
        )

    loc_ids = sorted(
        {
            int(lid)
            for lid in (loc.id, buffer_slot.id if buffer_slot else None)
            if lid is not None
        }
    )
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[operator_id],
    )
    db.commit()

    if not buffer_slot:
        publish_event(
            "floor.changed",
            {
                "reason": "washing_released_queued",
                "location_ids": loc_ids,
                "container_code": clean_code,
            },
            user_ids=recipient_user_ids,
            admins=True,
        )

    core.queue_service.try_resolve_waiting_slot_queue(
        db,
        lock_and_dispatch_fn=core.lock_cart_and_dispatch_fleet_task,
    )

    db.refresh(transport_req)
    return transport_req


def complete_washing_and_return_empty_cart(
    core,
    db: Session,
    container_code: str,
    operator_id: Optional[int] = None,
) -> TransportRequest:
    """Facade → ReturnEmptyCartUseCase."""
    from app.application.production.use_cases.cnc_operations.return_empty_cart import (
        ReturnEmptyCartRequest,
    )
    from app.infrastructure.di.production_factory import build_return_empty_cart_use_case

    result = build_return_empty_cart_use_case(db, core=core).execute(
        ReturnEmptyCartRequest(container_code=container_code, operator_id=operator_id)
    )
    orm = db.query(TransportRequest).filter(TransportRequest.id == result.id).first()
    if not orm:
        raise ValueError(f"TransportRequest id={result.id} missing after return_empty_cart")
    return orm
