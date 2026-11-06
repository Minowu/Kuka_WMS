"""Business logic for Admin Container / Rack Management (List, Remove via containerOut, Update Location)."""

from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import bind_context, get_logger
from app.modules.production.dispatch_service import dispatch_service
from app.modules.production.production_models import FleetTask, TransportRequest
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.dispatch")

ACTIVE_TASK_STATUSES = ("created", "pending_submit", "submitting", "sent", "dispatched", "in_progress")
ACTIVE_REQUEST_STATUSES = ("pending", "queued_for_cart", "queued_for_slot", "in_progress")


def _evaluate_rack_block_reason(
    cart: ItemStock,
    active_task: Optional[FleetTask],
    active_req: Optional[TransportRequest],
) -> tuple[bool, Optional[str]]:
    """
    Kiểm tra xem Rack có được phép xóa hoặc đổi vị trí hay không.
    Trả về `(can_modify, block_reason)`.
    """
    if not cart.is_active:
        return False, "Rack đã được thu hồi / không còn hoạt động trên xưởng."

    if cart.is_locked:
        m_code = cart.locked_by_mission_code or (active_task.mission_code if active_task else "AMR")
        return False, f"Rack đang bị khóa bởi nhiệm vụ điều xe AMR ({m_code}). Không thể xóa hoặc đổi vị trí khi xe đang chạy."

    if active_task:
        return (
            False,
            f"Rack đang nằm trong nhiệm vụ AMR '{active_task.mission_code}' (trạng thái: {active_task.status}).",
        )

    if active_req:
        return (
            False,
            f"Rack đang nằm trong yêu cầu/hàng đợi vận chuyển '{active_req.request_code}' (trạng thái: {active_req.status}).",
        )

    return True, None


def serialize_rack(
    cart: ItemStock,
    active_task: Optional[FleetTask] = None,
    active_req: Optional[TransportRequest] = None,
) -> dict[str, Any]:
    loc = cart.location
    dest_loc = cart.destination_location
    item = cart.item
    machine_code = None
    if loc and getattr(loc, "machine", None):
        machine_code = loc.machine.machine_code

    can_modify, block_reason = _evaluate_rack_block_reason(cart, active_task, active_req)

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
        "fleet_registered": bool(cart.fleet_registered),
        "created_at": cart.created_at,
        "updated_at": cart.updated_at,
    }


def list_racks(
    db: Session,
    include_inactive: bool = False,
    search: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Lấy danh sách các Container/Rack trên xưởng kèm trạng thái khóa và hàng đợi."""
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

    # Tải theo lô các FleetTask và TransportRequest đang hoạt động của các rack này
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

    items = [
        serialize_rack(
            c,
            active_task=task_by_cart_id.get(c.id),
            active_req=req_by_cart_id.get(c.id),
        )
        for c in carts
    ]

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


def _ensure_rack_modifiable(db: Session, cart: ItemStock, action_label: str) -> None:
    """
    Kiểm tra nghiêm ngặt các điều kiện chặn trước khi cho phép xóa hoặc đổi vị trí Rack:
    1. Rack đã bị thu hồi (`is_active == False`).
    2. Rack đang bị khóa bởi nhiệm vụ điều xe (`is_locked == True`).
    3. Rack đang có `FleetTask` đang chạy (`created`, `pending_submit`, `submitting`, `sent`, `in_progress`).
    4. Rack đang nằm trong `TransportRequest` / Hàng đợi tự động (`pending`, `queued_for_cart`, `queued_for_slot`, `in_progress`).
    """
    active_task = (
        db.query(FleetTask)
        .filter(
            FleetTask.container_id == cart.id,
            FleetTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(FleetTask.id.desc())
        .first()
    )
    active_req = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.container_id == cart.id,
            TransportRequest.status.in_(ACTIVE_REQUEST_STATUSES),
        )
        .order_by(TransportRequest.id.desc())
        .first()
    )

    can_modify, block_reason = _evaluate_rack_block_reason(cart, active_task, active_req)
    if not can_modify:
        raise ValueError(f"Không thể {action_label} Rack '{cart.container_code}': {block_reason}")


def remove_rack_container(
    db: Session,
    rack_id: int,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Xóa / thu hồi Container (Rack) khỏi vị trí hiện tại — giống hệt cơ chế gọi API `/amr/containerOut`
    khi xe rỗng về bãi xe trống (`EMPTY_CART_BUFFER`):
    1. Chặn nếu Rack đang khóa, đang di chuyển trên AMR hoặc đang nằm trong hàng đợi điều phối.
    2. Gửi lệnh `fleet_container_out` (`POST /amr/containerOut`) sang KUKA Fleet.
       - Nếu KUKA Fleet báo lỗi hoặc từ chối: Lưu log `FleetApiCall`, giữ nguyên trạng thái Rack trong WMS DB
         (không xóa trong DB để tránh lệch dữ liệu với Fleet) và trả về thông báo lỗi chi tiết cho người dùng.
    3. Chỉ khi KUKA Fleet xác nhận thành công (`code=0/200, success=True`), hệ thống mới giải phóng `ItemStock`
       trong CSDL (`is_active=False`, `location_id=None`, `status='empty'`, `fleet_registered=False`).
    """
    cart = (
        db.query(ItemStock)
        .filter(ItemStock.id == rack_id)
        .with_for_update(of=ItemStock)
        .first()
    )
    if not cart:
        raise ValueError(f"Không tìm thấy Rack (ID={rack_id}).")

    _ensure_rack_modifiable(db, cart, "xóa")

    old_loc_id = cart.location_id
    loc = db.query(Location).filter(Location.id == old_loc_id).first() if old_loc_id else None
    loc_code = loc.location_code if loc else ""
    loc_display = (loc.location_name or loc.location_code) if loc else "Chưa rõ vị trí"
    c_code = (cart.container_code or "").strip()

    if not c_code:
        raise ValueError("Rack không có mã container_code hợp lệ.")

    bind_context(container_code=c_code, station_code=loc_code)

    # Gửi lệnh containerOut sang KUKA Fleet TRƯỚC KHI thay đổi trạng thái ItemStock trong DB
    try:
        dispatch_service.fleet_container_out(
            location_code=loc_code,
            container_code=c_code,
            db=db,
        )
    except Exception as e:
        # Lưu lại bản ghi audit log FleetApiCall vào DB nhưng KHÔNG chạm vào ItemStock
        db.commit()
        logger.error(
            "Xóa Rack '%s' tại '%s' thất bại do KUKA Fleet báo lỗi containerOut: %s",
            c_code,
            loc_code,
            e,
            exc_info=True,
        )
        raise ValueError(
            f"Không thể xóa Rack '{c_code}' tại vị trí '{loc_display}' vì KUKA Fleet báo lỗi: {e}"
        ) from e

    # KUKA Fleet đã xóa thành công -> Cập nhật giải phóng Rack trong WMS DB
    cart.location_id = None
    cart.destination_location_id = None
    cart.quantity = 0
    cart.current_stage_level = 0
    cart.status = "empty"
    cart.is_active = False
    cart.is_locked = False
    cart.locked_by_mission_code = None
    cart.fleet_registered = False

    loc_ids = [int(old_loc_id)] if old_loc_id is not None else []
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[operator_id],
    )

    db.commit()
    db.refresh(cart)

    # Thử giải phóng hàng đợi WAITING_SLOT nếu ô vừa được giải phóng có xe đang chờ vào
    try:
        dispatch_service.try_resolve_waiting_slot_queue(db)
    except Exception as exc:
        logger.warning("Queue scan after rack removal failed: %s", exc)

    publish_event(
        "floor.changed",
        {
            "reason": "rack_removed",
            "location_ids": loc_ids,
            "container_code": c_code,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    return {
        "success": True,
        "message": f"Đã xóa Rack '{c_code}' khỏi vị trí '{loc_display}' và đồng bộ containerOut trên KUKA Fleet thành công.",
        "rack": serialize_rack(cart),
    }


def update_rack_location(
    db: Session,
    rack_id: int,
    new_location_id: int,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Cập nhật vị trí mới cho Container (Rack):
    1. Kiểm tra điều kiện chặn: Không cho đổi vị trí nếu Rack đang khóa, đang chạy nhiệm vụ AMR hoặc đang trong hàng đợi.
    2. Kiểm tra vị trí đích hợp lệ, đang hoạt động và chưa có Rack khác đỗ.
    3. Đồng bộ với KUKA Fleet theo giao thức chuẩn:
       - Bước 1: Gửi `containerOut` tại vị trí cũ (nếu có). Nếu Fleet báo lỗi -> Dừng ngay và giữ nguyên DB.
       - Bước 2: Gửi `containerIn` tại vị trí mới. Nếu Fleet từ chối vị trí mới -> Tự động gọi `containerIn` khôi phục lại vị trí cũ trên Fleet, giữ nguyên DB và báo lỗi chi tiết.
    4. Cập nhật `location_id` của `ItemStock` trong CSDL và phát sự kiện WebSocket `floor.changed`.
    """
    cart = (
        db.query(ItemStock)
        .filter(ItemStock.id == rack_id)
        .with_for_update(of=ItemStock)
        .first()
    )
    if not cart:
        raise ValueError(f"Không tìm thấy Rack (ID={rack_id}).")

    _ensure_rack_modifiable(db, cart, "đổi vị trí")

    if cart.location_id == new_location_id:
        raise ValueError("Vị trí mới trùng với vị trí hiện tại của Rack.")

    new_loc = (
        db.query(Location)
        .filter(Location.id == new_location_id, Location.is_active.is_(True))
        .first()
    )
    if not new_loc:
        raise ValueError(f"Vị trí đích (ID={new_location_id}) không tồn tại hoặc đã bị khóa.")

    new_loc_display = new_loc.location_name or new_loc.location_code

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

    # Kiểm tra xem vị trí đích có đang được AMR khác nhắm tới làm điểm hạ hàng không
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
            db.commit()  # Lưu log FleetApiCall nhưng giữ nguyên ItemStock
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
        # Nếu đã gỡ khỏi vị trí cũ trên Fleet nhưng thêm vào vị trí mới bị Fleet từ chối -> Khôi phục lại vị trí cũ trên Fleet!
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

        db.commit()  # Lưu log FleetApiCall nhưng giữ nguyên ItemStock tại vị trí cũ
        raise ValueError(
            f"KUKA Fleet từ chối đặt Rack '{c_code}' vào vị trí mới '{new_loc_display}' (containerIn): {in_err}{rollback_note}"
        ) from in_err

    # Chỉ cập nhật vị trí (location_id); giữ nguyên 100% current_stage_level, item_id, quantity của Rack
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
