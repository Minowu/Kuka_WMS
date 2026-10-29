"""Queue Management & Always-Scan Engine for TransportQueue (WAITING_CART & WAITING_SLOT)."""

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.production_models import FleetTask, TransportQueue, TransportRequest
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("main")


class QueueService:
    """Manages WAITING_CART and WAITING_SLOT queues with dual-trigger resolution."""

    def __init__(self, cart_selector: CartSelector):
        self.selector = cart_selector

    def try_resolve_waiting_cart_queue(
        self,
        db: Session,
        stage_level: Optional[int] = None,
        lock_and_dispatch_fn: Optional[Callable[..., Any]] = None,
    ) -> int:
        """
        Scan `TransportQueue` (`WAITING_CART`) in FIFO order (`priority ASC, created_at ASC`).
        If `stage_level` is None, scans all pending `WAITING_CART` entries across all stage levels (Always Scan).
        If a cart is now available, lock it and dispatch a `FleetTask`.
        """
        query = db.query(TransportQueue).filter(
            TransportQueue.queue_type == "WAITING_CART",
            TransportQueue.status == "PENDING",
        )
        if stage_level is not None:
            query = query.filter(TransportQueue.target_stage_level == stage_level)

        pending_entries = (
            query.order_by(TransportQueue.priority.asc(), TransportQueue.created_at.asc())
            .with_for_update(of=TransportQueue, skip_locked=True)
            .all()
        )

        resolved_count = 0
        for entry in pending_entries:
            req = entry.request
            if not req or not req.item_id:
                continue
            if not self.selector.is_location_free(db, req.destination_location_id):
                continue

            dest_loc = db.query(Location).filter(Location.id == req.destination_location_id).first()
            cart = self.selector.find_fifo_available_cart(
                db,
                item_id=req.item_id,
                stage_level=req.required_stage_level,
                target_location=dest_loc,
            )
            if cart and lock_and_dispatch_fn:
                try:
                    entry.status = "RESOLVED"
                    entry.resolved_at = datetime.now(timezone.utc)
                    lock_and_dispatch_fn(
                        db=db,
                        transport_req=req,
                        cart=cart,
                        pickup_location_id=cart.location_id,
                        dropoff_location_id=req.destination_location_id,
                    )
                    resolved_count += 1
                except Exception as exc:
                    entry.status = "PENDING"
                    entry.resolved_at = None
                    logger.warning(
                        "Không thể dispatch nhiệm vụ cho hàng đợi WAITING_CART (req_id=%s, cart=%s): %s",
                        req.id, cart.container_code, exc
                    )

        if resolved_count:
            db.commit()
        return resolved_count

    def try_resolve_waiting_slot_queue(
        self,
        db: Session,
        lock_and_dispatch_fn: Optional[Callable[..., Any]] = None,
    ) -> int:
        """
        Scan `TransportQueue` (`WAITING_SLOT` / `WAITING_WASH_SLOT`) in FIFO order (`priority ASC, created_at ASC`).
        When a Washing slot or Empty Cart Buffer becomes free, dispatch the waiting cart.
        """
        pending_entries = (
            db.query(TransportQueue)
            .filter(
                TransportQueue.queue_type.in_(["WAITING_SLOT", "WAITING_WASH_SLOT"]),
                TransportQueue.status == "PENDING",
            )
            .order_by(TransportQueue.priority.asc(), TransportQueue.created_at.asc())
            .with_for_update(of=TransportQueue, skip_locked=True)
            .all()
        )

        resolved_count = 0
        for entry in pending_entries:
            req = entry.request
            if not req or not req.container_id:
                continue

            cart = db.query(ItemStock).filter(ItemStock.id == req.container_id).first()
            if not cart or cart.is_locked or not cart.location_id:
                continue

            target_slot: Optional[Location] = None
            if req.request_type in ("MOVE_TO_WASH", "SEND_TO_WASH"):
                target_slot = self.selector.find_available_slot_to_wash(db)
            elif req.request_type == "RETURN_EMPTY_CART":
                target_slot = self.selector.find_next_empty_buffer_slot(db)

            if target_slot and lock_and_dispatch_fn:
                try:
                    entry.status = "RESOLVED"
                    entry.resolved_at = datetime.now(timezone.utc)
                    lock_and_dispatch_fn(
                        db=db,
                        transport_req=req,
                        cart=cart,
                        pickup_location_id=cart.location_id,
                        dropoff_location_id=target_slot.id,
                    )
                    resolved_count += 1
                except Exception as exc:
                    entry.status = "PENDING"
                    entry.resolved_at = None
                    logger.warning(
                        "Không thể dispatch nhiệm vụ cho hàng đợi WAITING_SLOT (req_id=%s, slot=%s): %s",
                        req.id, target_slot.location_code, exc
                    )

        if resolved_count:
            db.commit()
        return resolved_count
