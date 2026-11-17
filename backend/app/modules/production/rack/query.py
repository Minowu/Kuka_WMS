"""Business logic for Admin Container / Rack Management & Transport Request Cancellation."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import bind_context, get_logger
from app.modules.auth.auth_model import User
from app.modules.production.dispatch.service import dispatch_service
from app.modules.production.production_models import (
    FleetTask,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportQueue,
    TransportRequest,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.dispatch")

ACTIVE_TASK_STATUSES = ("created", "pending_submit", "submitting", "sent", "dispatched", "in_progress")
ACTIVE_REQUEST_STATUSES = ("pending", "queued_for_cart", "queued_for_slot", "in_progress")
from app.modules.production.rack.policy import (
    _build_route_context_by_item,
    _evaluate_rack_block_reason,
)

def serialize_rack(
    cart: ItemStock,
    active_task: Optional[FleetTask] = None,
    active_req: Optional[TransportRequest] = None,
    allowed_location_ids: Optional[list[int]] = None,
) -> dict[str, Any]:
    loc = cart.location
    dest_loc = cart.destination_location
    item = cart.item
    machine_code = None
    if loc and getattr(loc, "machine", None):
        machine_code = loc.machine.machine_code

    can_modify, block_reason, can_relocate, relocate_block_reason = _evaluate_rack_block_reason(
        cart, active_task, active_req
    )

    return {
        "id": cart.id,
        "container_code": cart.container_code or f"RACK-{cart.id}",
        "item_id": cart.item_id,
        "item_sku": item.sku if item else None,
        "item_name": item.name if item else None,
        "location_id": cart.location_id,
        "location_code": loc.location_code if loc else None,
        "location_label": loc.location_label if loc else None,
        "location_name": (loc.location_name or loc.location_code) if loc else None,
        "location_type": loc.location_type if loc else None,
        "machine_code": machine_code,
        "destination_location_id": cart.destination_location_id,
        "destination_location_name": (dest_loc.location_name or dest_loc.location_code) if dest_loc else None,
        "quantity": float(cart.quantity or 0),
        "current_stage_level": int(cart.current_stage_level or 0),
        "status": cart.status or "available",
        "is_active": bool(cart.is_active),
        "is_locked": bool(cart.is_locked),
        "locked_by_mission_code": cart.locked_by_mission_code or (active_task.mission_code if active_task else None),
        "active_request_code": active_req.request_code if active_req else None,
        "active_request_status": active_req.status if active_req else None,
        "can_modify": can_modify,
        "block_reason": block_reason,
        "can_relocate": can_relocate,
        "relocate_block_reason": relocate_block_reason,
        "allowed_location_ids": allowed_location_ids if allowed_location_ids is not None else [],
        "fleet_registered": bool(cart.fleet_registered),
        "created_at": cart.created_at,
        "updated_at": cart.updated_at,
    }

def list_racks(
    db: Session,
    include_inactive: bool = False,
    search: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Lấy danh sách các Container/Rack trên xưởng kèm trạng thái khóa, hàng đợi và danh sách vị trí đích hợp lệ."""
    query = (
        db.query(ItemStock)
        .options(
            joinedload(ItemStock.item),
            joinedload(ItemStock.location).joinedload(Location.machine),
            joinedload(ItemStock.destination_location),
        )
        .filter(ItemStock.container_code.isnot(None))
    )
    if not include_inactive:
        query = query.filter(ItemStock.is_active.is_(True))

    carts = (
        query.order_by(
            ItemStock.is_active.desc(),
            ItemStock.updated_at.desc().nullslast(),
            ItemStock.id.desc(),
        )
        .all()
    )
    if not carts:
        return []

    cart_ids = [c.id for c in carts]
    item_ids = {c.item_id for c in carts if c.item_id is not None}

    active_tasks = (
        db.query(FleetTask)
        .filter(
            FleetTask.container_id.in_(cart_ids),
            FleetTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(FleetTask.id.desc())
        .all()
    )
    task_by_cart_id: dict[int, FleetTask] = {}
    for t in active_tasks:
        if t.container_id and t.container_id not in task_by_cart_id:
            task_by_cart_id[t.container_id] = t

    active_reqs = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.container_id.in_(cart_ids),
            TransportRequest.status.in_(ACTIVE_REQUEST_STATUSES),
        )
        .order_by(TransportRequest.id.desc())
        .all()
    )
    req_by_cart_id: dict[int, TransportRequest] = {}
    for r in active_reqs:
        if r.container_id and r.container_id not in req_by_cart_id:
            req_by_cart_id[r.container_id] = r

    # Tiền nạp danh sách vị trí active và quy trình để tính sẵn allowed_location_ids cho từng Rack
    all_active_locs = (
        db.query(Location)
        .filter(
            Location.is_active.is_(True),
            Location.location_type.in_(["RAW_MATERIAL", "CNC_SLOT", "WASHING_SLOT"]),
        )
        .all()
    )
    route_ctx_by_item = _build_route_context_by_item(db, item_ids)

    items = []
    for c in carts:
        r_ctx = route_ctx_by_item.get(c.item_id) if c.item_id else None
        allowed_ids: list[int] = []
        if c.is_active and c.status not in ("empty", "out_failed"):
            for loc in all_active_locs:
                if loc.id == c.location_id:
                    continue
                ok, _ = _validate_location_for_cart(c, loc, r_ctx)
                if ok:
                    allowed_ids.append(loc.id)

        items.append(
            serialize_rack(
                c,
                active_task=task_by_cart_id.get(c.id),
                active_req=req_by_cart_id.get(c.id),
                allowed_location_ids=allowed_ids,
            )
        )

    if search and search.strip():
        kw = search.strip().lower()
        items = [
            r
            for r in items
            if kw in (r["container_code"] or "").lower()
            or kw in (r["location_name"] or "").lower()
            or kw in (r["location_code"] or "").lower()
            or kw in (r["location_label"] or "").lower()
            or kw in (r["item_sku"] or "").lower()
            or kw in (r["item_name"] or "").lower()
            or kw in (r["machine_code"] or "").lower()
        ]
    return items
