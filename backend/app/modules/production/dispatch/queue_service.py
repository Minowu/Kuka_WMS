"""Queue Management & Always-Scan Engine for TransportQueue (WAITING_CART & WAITING_SLOT)."""

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.core.logger import bind_context, get_logger, log_context
from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.production_models import FleetTask, TransportQueue, TransportRequest
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("wms.dispatch")


class QueueService:
    """Manages WAITING_CART and WAITING_SLOT queues with dual-trigger resolution."""

    def __init__(self, cart_selector: CartSelector):
        self.selector = cart_selector

    def enqueue(
        self,
        db: Session,
        request_id: int,
        queue_type: str,
        target_stage_level: Optional[int] = None,
        priority: int = 10,
    ) -> TransportQueue:
        """Enqueue a request into TransportQueue and log the enqueue event and new queue length."""
        entry = TransportQueue(
            request_id=request_id,
            queue_type=queue_type,
            target_stage_level=target_stage_level,
            status="PENDING",
            priority=priority,
        )
        db.add(entry)
        db.flush()

        queue_length = (
            db.query(TransportQueue)
            .filter(TransportQueue.queue_type == queue_type, TransportQueue.status == "PENDING")
            .count()
        )
        logger.info(
            "Enqueued TransportRequest %s into %s (entry_id=%s, target_stage_level=%s, priority=%s). Queue length: %d",
            request_id,
            queue_type,
            entry.id,
            target_stage_level,
            priority,
            queue_length,
            extra={
                "transport_request_id": request_id,
                "queue_type": queue_type,
                "queue_length": queue_length,
            },
        )
        return entry

    def dequeue(
        self,
        db: Session,
        entry: TransportQueue,
        reason: str = "resolved",
    ) -> None:
        """Dequeue (mark RESOLVED) an entry and log the dequeue event and remaining queue length."""
        old_status = entry.status
        entry.status = "RESOLVED"
        entry.resolved_at = datetime.now(timezone.utc)
        db.flush()

        remaining_length = (
            db.query(TransportQueue)
            .filter(TransportQueue.queue_type == entry.queue_type, TransportQueue.status == "PENDING")
            .count()
        )
        logger.info(
            "Dequeued entry id=%s from %s: %s -> RESOLVED (reason: %s, request_id=%s). Remaining queue length: %d",
            entry.id,
            entry.queue_type,
            old_status,
            reason,
            entry.request_id,
            remaining_length,
            extra={
                "transport_request_id": entry.request_id,
                "queue_type": entry.queue_type,
                "queue_length": remaining_length,
            },
        )

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
        logger.info(
            "Queue processing attempt: starting WAITING_CART queue scan (target_stage_level=%s)",
            stage_level,
        )
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

        queue_length = len(pending_entries)
        logger.info(
            "WAITING_CART queue length: %d pending entries (target_stage_level=%s)",
            queue_length,
            stage_level,
            extra={"queue_type": "WAITING_CART", "queue_length": queue_length},
        )

        resolved_count = 0
        for entry in pending_entries:
            req = entry.request
            if not req or not req.item_id:
                logger.debug(
                    "Skipping queue entry id=%s: missing request or item_id",
                    entry.id,
                )
                continue
            if not self.selector.is_location_free(db, req.destination_location_id):
                logger.debug(
                    "Skipping queue entry id=%s: destination location id=%s is not free",
                    entry.id,
                    req.destination_location_id,
                    extra={"transport_request_id": req.id},
                )
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
                    self.dequeue(
                        db,
                        entry,
                        reason=f"cart {cart.container_code} found for destination {dest_loc.location_code if dest_loc else req.destination_location_id}",
                    )
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
                        req.id,
                        cart.container_code,
                        exc,
                        extra={"transport_request_id": req.id, "container_code": cart.container_code},
                        exc_info=True,
                    )

        logger.info(
            "Finished WAITING_CART queue scan: resolved %d / %d entries",
            resolved_count,
            queue_length,
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
        logger.info("Queue processing attempt: starting WAITING_SLOT queue scan")
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

        queue_length = len(pending_entries)
        logger.info(
            "WAITING_SLOT queue length: %d pending entries",
            queue_length,
            extra={"queue_type": "WAITING_SLOT", "queue_length": queue_length},
        )

        resolved_count = 0
        for entry in pending_entries:
            req = entry.request
            if not req or not req.container_id:
                logger.debug(
                    "Skipping queue entry id=%s: missing request or container_id",
                    entry.id,
                )
                continue

            cart = db.query(ItemStock).filter(ItemStock.id == req.container_id).first()
            if not cart or cart.is_locked or not cart.location_id:
                logger.debug(
                    "Skipping queue entry id=%s: cart %s is invalid, locked, or has no location",
                    entry.id,
                    cart.container_code if cart else "none",
                )
                continue

            target_slot: Optional[Location] = None
            if req.request_type in ("MOVE_TO_WASH", "SEND_TO_WASH"):
                target_slot = self.selector.find_available_slot_to_wash(db)
            elif req.request_type == "RETURN_EMPTY_CART":
                target_slot = self.selector.find_next_empty_buffer_slot(db)

            if target_slot and lock_and_dispatch_fn:
                try:
                    self.dequeue(
                        db,
                        entry,
                        reason=f"slot {target_slot.location_code} became available for cart {cart.container_code}",
                    )
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
                        req.id,
                        target_slot.location_code,
                        exc,
                        extra={"transport_request_id": req.id, "station_code": target_slot.location_code},
                        exc_info=True,
                    )

        logger.info(
            "Finished WAITING_SLOT queue scan: resolved %d / %d entries",
            resolved_count,
            queue_length,
        )
        if resolved_count:
            db.commit()
        return resolved_count
