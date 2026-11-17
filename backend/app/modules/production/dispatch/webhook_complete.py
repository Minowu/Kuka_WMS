"""Fleet task completion handler (extracted from WebhookHandler)."""

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.core.logger import bind_context, get_logger
from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient
from app.modules.production.production_models import FleetTask
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.fleet.webhook")


def complete_fleet_task(
    fleet_client: KukaFleetClient,
    db: Session,
    mission_code: str,
    on_after_complete_fn: Optional[Callable[..., Any]] = None,
) -> FleetTask:
    """Official completion handler when KUKA Fleet reports COMPLETED."""
    fleet_task = (
        db.query(FleetTask)
        .filter(FleetTask.mission_code == mission_code)
        .with_for_update(of=FleetTask)
        .first()
    )
    if not fleet_task:
        raise ValueError(f"Không tìm thấy FleetTask '{mission_code}'.")

    bind_context(fleet_task_id=fleet_task.id)
    old_status = fleet_task.status
    now = datetime.now(timezone.utc)
    fleet_task.status = "completed"
    fleet_task.completed_at = now
    fleet_task.updated_at = now

    if old_status != "completed":
        logger.info(
            "FleetTask %s status mapping transition: %s -> completed (via complete_fleet_task)",
            mission_code,
            old_status,
            extra={
                "fleet_task_id": fleet_task.id,
                "mission_code": mission_code,
                "old_status": old_status,
                "new_status": "completed",
                "kuka_status": "COMPLETED",
            },
        )

    req_type = None
    created_by = None
    if fleet_task.request:
        req_type = fleet_task.request.request_type
        created_by = fleet_task.request.created_by
        fleet_task.request.status = "completed"
        fleet_task.request.completed_at = now

    dropoff_loc = (
        db.query(Location).filter(Location.id == fleet_task.dropoff_location_id).first()
        if fleet_task.dropoff_location_id
        else None
    )
    is_empty_buffer_dropoff = bool(
        req_type == "RETURN_EMPTY_CART"
        or (dropoff_loc and dropoff_loc.location_type == "EMPTY_CART_BUFFER")
    )

    container_out_err_note: Optional[str] = None
    if fleet_task.container_id:
        cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
        if cart:
            if is_empty_buffer_dropoff:
                container_out_ok = True
                container_out_err = None
                if dropoff_loc and cart.container_code:
                    try:
                        fleet_client.fleet_container_out(
                            location_code=dropoff_loc.location_code,
                            container_code=cart.container_code,
                            db=db,
                        )
                    except Exception as e:
                        container_out_ok = False
                        container_out_err = str(e)
                        logger.error(
                            "Fleet containerOut failed for container=%s at buffer=%s: %s",
                            cart.container_code,
                            dropoff_loc.location_code,
                            e,
                        )

                if container_out_ok:
                    cart.location_id = None
                    cart.destination_location_id = None
                    cart.quantity = 0
                    cart.current_stage_level = 0
                    cart.status = "empty"
                    cart.is_active = False
                    cart.is_locked = False
                    cart.locked_by_mission_code = None
                    cart.fleet_registered = False
                else:
                    # Không nuốt lỗi: Giữ xe tại vị trí bãi đệm với trạng thái 'out_failed'
                    # và fleet_registered=True để WMS biết ô đệm này trên Fleet vẫn đang bị chiếm!
                    cart.location_id = fleet_task.dropoff_location_id
                    cart.destination_location_id = None
                    cart.quantity = 0
                    cart.current_stage_level = 0
                    cart.status = "out_failed"
                    cart.is_active = True
                    cart.is_locked = False
                    cart.locked_by_mission_code = None
                    cart.fleet_registered = True
                    container_out_err_note = f"AMR đã hạ xe nhưng lỗi xóa xe trên Fleet (containerOut): {container_out_err}"
                    fleet_task.error_message = container_out_err_note
            else:
                cart.location_id = fleet_task.dropoff_location_id
                cart.destination_location_id = None
                cart.is_locked = False
                cart.locked_by_mission_code = None
                cart.status = "available"

    loc_ids = sorted(
        {
            int(lid)
            for lid in (fleet_task.pickup_location_id, fleet_task.dropoff_location_id)
            if lid is not None
        }
    )
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[created_by],
    )

    db.commit()

    if container_out_err_note:
        publish_event(
            "fleet.task_failed",
            {
                "mission_code": mission_code,
                "location_id": fleet_task.pickup_location_id or fleet_task.dropoff_location_id,
                "location_ids": loc_ids,
                "container_code": fleet_task.container_code,
                "request_type": req_type or "RETURN_EMPTY_CART",
                "message": container_out_err_note,
            },
            user_ids=recipient_user_ids,
            admins=True,
        )

    publish_event(
        "floor.changed",
        {
            "reason": "task_completed",
            "mission_code": mission_code,
            "location_ids": loc_ids,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    if on_after_complete_fn:
        on_after_complete_fn(db)

    return fleet_task
