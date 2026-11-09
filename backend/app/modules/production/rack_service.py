"""Business logic for Admin Container / Rack Management & Transport Request Cancellation."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import bind_context, get_logger
from app.modules.auth.auth_model import User
from app.modules.production.dispatch_service import dispatch_service
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


def _evaluate_rack_block_reason(
    cart: ItemStock,
    active_task: Optional[FleetTask],
    active_req: Optional[TransportRequest],
) -> tuple[bool, Optional[str], bool, Optional[str]]:
    """
    Kiểm tra xem Rack có được phép xóa (`can_modify`) hoặc đổi vị trí (`can_relocate`) hay không.
    Trả về `(can_modify, block_reason, can_relocate, relocate_block_reason)`.
    """
    if not cart.is_active:
        reason = "Rack đã được thu hồi / không còn hoạt động trên xưởng."
        return False, reason, False, reason

    if cart.is_locked:
        m_code = cart.locked_by_mission_code or (active_task.mission_code if active_task else "AMR")
        reason = f"Rack đang bị khóa bởi nhiệm vụ điều xe AMR ({m_code}). Không thể xóa hoặc đổi vị trí khi xe đang chạy."
        return False, reason, False, reason

    if active_task:
        reason = f"Rack đang nằm trong nhiệm vụ AMR '{active_task.mission_code}' (trạng thái: {active_task.status})."
        return False, reason, False, reason

    if active_req:
        reason = f"Rack đang nằm trong yêu cầu/hàng đợi vận chuyển '{active_req.request_code}' (trạng thái: {active_req.status}). Vui lòng hủy yêu cầu trước."
        return False, reason, False, reason

    if cart.status in ("empty", "out_failed"):
        reloc_reason = (
            "Rack đang ở trạng thái xe rỗng / lỗi xóa trên Fleet (out_failed) — "
            "chỉ được phép bấm 'Xóa Rack' để thu hồi, không được đổi vị trí."
        )
        return True, None, False, reloc_reason

    return True, None, True, None


def _build_route_context_by_item(
    db: Session,
    item_ids: set[int],
) -> dict[int, dict[str, Any]]:
    """
    Tiền nạp thông tin Quy trình đang active (`ProductionRoute`) cho danh sách `item_ids`:
    Trả về `{item_id: {"max_stage": int, "machine_stages": {machine_id: set[int]}}}`.
    """
    if not item_ids:
        return {}

    routes = (
        db.query(ProductionRoute)
        .options(
            joinedload(ProductionRoute.steps)
            .joinedload(RouteStep.allowed_machine_links)
        )
        .filter(
            ProductionRoute.item_id.in_(list(item_ids)),
            ProductionRoute.is_active.is_(True),
        )
        .all()
    )
    result: dict[int, dict[str, Any]] = {}
    for route in routes:
        steps = route.steps or []
        max_stage = max((st.stage_level for st in steps), default=0)
        machine_stages: dict[int, set[int]] = {}
        for st in steps:
            for link in st.allowed_machine_links or []:
                if link.machine_id is not None:
                    machine_stages.setdefault(link.machine_id, set()).add(st.stage_level)
        result[route.item_id] = {
            "route_id": route.id,
            "max_stage": max_stage,
            "machine_stages": machine_stages,
        }
    return result


def _validate_location_for_cart(
    cart: ItemStock,
    loc: Location,
    route_ctx: Optional[dict[str, Any]],
) -> tuple[bool, Optional[str]]:
    """
    Kiểm tra xem một Rack (`cart`) có được phép chuyển tới vị trí `loc` theo đúng logic công đoạn sản xuất không:
    1. Không bao giờ cho phép chuyển Rack sang `EMPTY_CART_BUFFER` (muốn thu hồi xe rỗng phải dùng Xóa Rack).
    2. `RAW_MATERIAL`: Chỉ nhận xe phôi thô (`current_stage_level == 0`).
    3. `CNC_SLOT`: Máy CNC tại vị trí đó phải thuộc Quy trình (`ProductionRoute`) đang active của Model trên xe,
       và bước công đoạn `S` của máy phải khớp với trạng thái hiện tại của xe (`cart_level in (S - 1, S)`).
    4. `WASHING_SLOT`: Chỉ nhận xe đã hoàn thành bước CNC cuối cùng (`cart_level >= max_stage` và `max_stage > 0`).
    """
    loc_display = loc.location_name or loc.location_code
    loc_type = loc.location_type
    cart_level = int(cart.current_stage_level or 0)
    item_name = cart.item.name if cart.item else f"Model ID={cart.item_id}"

    if loc_type == "EMPTY_CART_BUFFER":
        return (
            False,
            f"Không được phép chuyển Rack vào Bãi Xe Trống ('{loc_display}'). Nếu muốn thu hồi xe rỗng, vui lòng dùng chức năng 'Xóa Rack'.",
        )

    if loc_type == "RAW_MATERIAL":
        if cart_level != 0:
            return (
                False,
                f"Rack đang ở công đoạn Lv {cart_level} (bán thành phẩm), không thể chuyển ngược về Khu Nguyên Liệu '{loc_display}' (chỉ dành cho phôi thô Lv 0).",
            )
        return True, None

    if not cart.item_id or not route_ctx:
        return (
            False,
            f"Model '{item_name}' trên Rack chưa có Quy trình sản xuất (Route) đang kích hoạt, không thể chuyển vào '{loc_display}'.",
        )

    max_stage = int(route_ctx.get("max_stage") or 0)
    machine_stages: dict[int, set[int]] = route_ctx.get("machine_stages") or {}

    if loc_type == "CNC_SLOT":
        if not loc.machine_id or loc.machine_id not in machine_stages:
            return (
                False,
                f"Trạm máy CNC tại '{loc_display}' không nằm trong Quy trình sản xuất của Model '{item_name}'.",
            )
        allowed_stages = machine_stages[loc.machine_id]
        # Máy ở Bước S hợp lệ khi xe đang là đầu vào của Bước S (Lv = S - 1) hoặc vừa xong tại Bước S (Lv = S)
        valid_for_machine = any(cart_level in (s - 1, s) for s in allowed_stages)
        if not valid_for_machine:
            stages_str = ", ".join(f"Bước {s} (nhận phôi Lv {s - 1})" for s in sorted(allowed_stages))
            return (
                False,
                f"Rack đang ở công đoạn Lv {cart_level}, không khớp với công đoạn của máy tại '{loc_display}' ({stages_str}).",
            )
        return True, None

    if loc_type == "WASHING_SLOT":
        if max_stage <= 0 or cart_level < max_stage:
            return (
                False,
                f"Rack mới ở công đoạn Lv {cart_level} (chưa hoàn thành bước CNC cuối Lv {max_stage} của Model '{item_name}'), không thể chuyển thẳng vào Khu Tẩy Rửa '{loc_display}'.",
            )
        return True, None

    return False, f"Loại vị trí '{loc_type}' tại '{loc_display}' không hợp lệ để đặt Rack."


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


def _ensure_rack_modifiable(
    db: Session,
    cart: ItemStock,
    action_label: str,
    require_relocatable: bool = False,
) -> None:
    """Kiểm tra nghiêm ngặt các điều kiện chặn trước khi cho phép xóa hoặc đổi vị trí Rack."""
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

    can_modify, block_reason, can_relocate, relocate_block_reason = _evaluate_rack_block_reason(
        cart, active_task, active_req
    )
    if not can_modify:
        raise ValueError(f"Không thể {action_label} Rack '{cart.container_code}': {block_reason}")
    if require_relocatable and not can_relocate:
        raise ValueError(f"Không thể {action_label} Rack '{cart.container_code}': {relocate_block_reason}")


def remove_rack_container(
    db: Session,
    rack_id: int,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Xóa / thu hồi Container (Rack) khỏi vị trí hiện tại:
    1. Chặn nếu Rack đang khóa, đang di chuyển trên AMR hoặc đang nằm trong hàng đợi điều phối.
    2. Nếu Rack đang có vị trí (`loc_code`) và đã đăng ký trên Fleet (`fleet_registered=True`),
       gửi lệnh `fleet_container_out` (`POST /amr/containerOut`) sang KUKA Fleet.
       - Nếu KUKA Fleet báo lỗi: giữ nguyên trạng thái Rack trong WMS DB và trả về thông báo lỗi chi tiết.
    3. Nếu Rack đang bị treo không có vị trí (`location_id=None`) hoặc `fleet_registered=False`,
       cho phép thu hồi trực tiếp trong WMS DB để không bao giờ bị kẹt xe.
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

    _ensure_rack_modifiable(db, cart, "xóa", require_relocatable=False)

    old_loc_id = cart.location_id
    loc = db.query(Location).filter(Location.id == old_loc_id).first() if old_loc_id else None
    loc_code = (loc.location_code or "").strip() if loc else ""
    loc_display = (loc.location_name or loc.location_code) if loc else "Bãi trống / Chưa rõ vị trí"
    c_code = (cart.container_code or "").strip()

    if not c_code:
        raise ValueError("Rack không có mã container_code hợp lệ.")

    bind_context(container_code=c_code, station_code=loc_code or None)

    # Chỉ gọi containerOut sang KUKA Fleet khi Rack thực sự có mã vị trí và đã đăng ký trên Fleet
    called_fleet_out = False
    if loc_code and cart.fleet_registered:
        try:
            dispatch_service.fleet_container_out(
                location_code=loc_code,
                container_code=c_code,
                db=db,
            )
            called_fleet_out = True
        except Exception as e:
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

    try:
        dispatch_service.try_resolve_waiting_slot_queue(db)
        dispatch_service.try_resolve_waiting_cart_queue(db)
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

    msg = (
        f"Đã xóa Rack '{c_code}' khỏi vị trí '{loc_display}' và đồng bộ containerOut trên KUKA Fleet thành công."
        if called_fleet_out
        else f"Đã thu hồi Rack '{c_code}' khỏi WMS thành công."
    )
    return {
        "success": True,
        "message": msg,
        "rack": serialize_rack(cart),
    }


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
