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
    _ensure_rack_modifiable,
    _validate_location_for_cart,
)
from app.modules.production.rack.query import serialize_rack

def update_rack_location(
    db: Session,
    rack_id: int,
    new_location_id: int,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Cập nhật vị trí mới cho Container (Rack) với đầy đủ chốt chặn nghiệp vụ:
    1. Chặn nếu Rack đang khóa, đang chạy nhiệm vụ AMR, đang trong hàng đợi, hoặc là xe rỗng/out_failed.
    2. Kiểm tra vị trí đích:
       - Đang hoạt động và chưa có Rack khác đỗ.
       - Không có nhiệm vụ AMR (`FleetTask`) đang chở hàng tới vị trí đích.
       - Không có yêu cầu gọi phôi (`TransportRequest` trạng thái `queued_for_cart`/`in_progress`) đang chờ tại vị trí đích.
       - Phù hợp với Quy trình (`ProductionRoute`) và bậc công đoạn (`current_stage_level`) của Model trên Rack.
    3. Đồng bộ 2 chiều với KUKA Fleet (`containerOut` vị trí cũ -> `containerIn` vị trí mới, tự động rollback nếu lỗi).
    """
    cart = (
        db.query(ItemStock)
        .options(joinedload(ItemStock.item))
        .filter(ItemStock.id == rack_id)
        .with_for_update(of=ItemStock)
        .first()
    )
    if not cart:
        raise ValueError(f"Không tìm thấy Rack (ID={rack_id}).")

    _ensure_rack_modifiable(db, cart, "đổi vị trí", require_relocatable=True)

    if cart.location_id == new_location_id:
        raise ValueError("Vị trí mới trùng với vị trí hiện tại của Rack.")

    new_loc = (
        db.query(Location)
        .options(joinedload(Location.machine))
        .filter(Location.id == new_location_id, Location.is_active.is_(True))
        .first()
    )
    if not new_loc:
        raise ValueError(f"Vị trí đích (ID={new_location_id}) không tồn tại hoặc đã bị khóa.")

    new_loc_display = new_loc.location_name or new_loc.location_code

    # Kiểm tra quy tắc công đoạn & quy trình đối với vị trí đích
    route_ctx_map = _build_route_context_by_item(db, {cart.item_id} if cart.item_id else set())
    route_ctx = route_ctx_map.get(cart.item_id) if cart.item_id else None
    is_valid_dest, dest_err = _validate_location_for_cart(cart, new_loc, route_ctx)
    if not is_valid_dest:
        raise ValueError(dest_err)

    occupying_cart = (
        db.query(ItemStock)
        .filter(
            ItemStock.location_id == new_loc.id,
            ItemStock.is_active.is_(True),
            ItemStock.id != cart.id,
        )
        .first()
    )
    if occupying_cart:
        raise ValueError(
            f"Vị trí '{new_loc_display}' đang có Rack '{occupying_cart.container_code}' đỗ. Vui lòng chọn vị trí trống."
        )

    incoming_task = (
        db.query(FleetTask)
        .filter(
            FleetTask.dropoff_location_id == new_loc.id,
            FleetTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .first()
    )
    if incoming_task:
        raise ValueError(
            f"Vị trí '{new_loc_display}' đang có AMR thực hiện nhiệm vụ '{incoming_task.mission_code}' chở hàng tới. Vui lòng chọn vị trí khác."
        )

    waiting_dest_req = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.destination_location_id == new_loc.id,
            TransportRequest.status.in_(ACTIVE_REQUEST_STATUSES),
        )
        .order_by(TransportRequest.id.desc())
        .first()
    )
    if waiting_dest_req:
        raise ValueError(
            f"Vị trí '{new_loc_display}' đang có yêu cầu gọi phôi '{waiting_dest_req.request_code}' ({waiting_dest_req.status}). "
            f"Vui lòng hủy yêu cầu gọi phôi tại vị trí này trước khi đặt Rack thủ công."
        )

    old_loc_id = cart.location_id
    old_loc = db.query(Location).filter(Location.id == old_loc_id).first() if old_loc_id else None
    old_loc_display = (old_loc.location_name or old_loc.location_code) if old_loc else "Chưa rõ"
    c_code = (cart.container_code or "").strip()

    bind_context(container_code=c_code, station_code=new_loc.location_code)

    removed_from_old_on_fleet = False
    if old_loc and old_loc.location_code and cart.fleet_registered:
        try:
            dispatch_service.fleet_container_out(
                location_code=old_loc.location_code,
                container_code=c_code,
                db=db,
            )
            removed_from_old_on_fleet = True
        except Exception as out_err:
            db.commit()
            logger.error(
                "Đổi vị trí Rack '%s' thất bại ở bước gỡ khỏi vị trí cũ '%s' (containerOut): %s",
                c_code,
                old_loc.location_code,
                out_err,
                exc_info=True,
            )
            raise ValueError(
                f"Không thể gỡ Rack '{c_code}' khỏi vị trí cũ '{old_loc_display}' trên KUKA Fleet (containerOut): {out_err}"
            ) from out_err

    try:
        dispatch_service.fleet_container_in(
            location_code=new_loc.location_code,
            container_code=c_code,
            is_new=False,
            db=db,
        )
    except Exception as in_err:
        rollback_note = ""
        if removed_from_old_on_fleet and old_loc and old_loc.location_code:
            try:
                dispatch_service.fleet_container_in(
                    location_code=old_loc.location_code,
                    container_code=c_code,
                    is_new=False,
                    db=db,
                )
                rollback_note = f" (Hệ thống đã tự động khôi phục lại Rack về vị trí cũ '{old_loc_display}' trên KUKA Fleet)."
            except Exception as restore_err:
                logger.error(
                    "Khôi phục Rack '%s' về vị trí cũ '%s' trên Fleet thất bại: %s",
                    c_code,
                    old_loc.location_code,
                    restore_err,
                )
                rollback_note = f" (Cảnh báo: Không thể khôi phục tự động về vị trí cũ '{old_loc_display}' trên Fleet: {restore_err})."

        db.commit()
        raise ValueError(
            f"KUKA Fleet từ chối đặt Rack '{c_code}' vào vị trí mới '{new_loc_display}' (containerIn): {in_err}{rollback_note}"
        ) from in_err

    cart.location_id = new_loc.id
    cart.destination_location_id = None
    cart.fleet_registered = True

    loc_ids = sorted({int(lid) for lid in (old_loc_id, new_loc.id) if lid is not None})
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[operator_id],
    )

    db.commit()
    db.refresh(cart)

    try:
        dispatch_service.try_resolve_waiting_slot_queue(db)
        dispatch_service.try_resolve_waiting_cart_queue(db)
    except Exception as exc:
        logger.warning("Queue scan after rack relocation failed: %s", exc)

    publish_event(
        "floor.changed",
        {
            "reason": "rack_location_updated",
            "location_ids": loc_ids,
            "container_code": c_code,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    return {
        "success": True,
        "message": f"Đã chuyển Rack '{c_code}' sang vị trí '{new_loc_display}' và đồng bộ KUKA Fleet thành công.",
        "rack": serialize_rack(cart),
    }
