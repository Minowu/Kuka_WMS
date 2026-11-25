"""Admin sync-bypass: đồng bộ vị trí/stage thủ công + audit production_record (W1/W2)."""

from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import bind_context, get_logger
from app.modules.production.dispatch.service import dispatch_service
from app.modules.production.production_models import (
    FleetTask,
    ProductionRecord,
    TransportRequest,
)
from app.modules.production.rack.policy import (
    _build_route_context_by_item,
    _ensure_rack_modifiable,
    _validate_location_for_cart,
)
from app.modules.production.rack.query import serialize_rack
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.dispatch")

ACTIVE_TASK_STATUSES = (
    "created",
    "pending_submit",
    "submitting",
    "sent",
    "dispatched",
    "in_progress",
)
ACTIVE_REQUEST_STATUSES = ("pending", "queued_for_cart", "queued_for_slot", "in_progress")

SyncBypassMode = Literal["SYNC_PHYSICAL", "DISPATCH_TO_WASH"]


def _require_note(note: Optional[str]) -> str:
    clean = (note or "").strip()
    if not clean:
        raise ValueError(
            "Bắt buộc nhập ghi chú (note) khi bypass /complete-stage để ghi production_record."
        )
    if len(clean) > 1000:
        raise ValueError("Ghi chú không được vượt quá 1000 ký tự.")
    return clean


def _load_rack_for_update(db: Session, rack_id: int) -> ItemStock:
    cart = (
        db.query(ItemStock)
        .options(joinedload(ItemStock.item))
        .filter(ItemStock.id == rack_id)
        .with_for_update(of=ItemStock)
        .first()
    )
    if not cart:
        raise ValueError(f"Không tìm thấy Rack (ID={rack_id}).")
    return cart


def _load_active_location(db: Session, location_id: int) -> Location:
    loc = (
        db.query(Location)
        .options(joinedload(Location.machine))
        .filter(Location.id == location_id, Location.is_active.is_(True))
        .first()
    )
    if not loc:
        raise ValueError(f"Vị trí đích (ID={location_id}) không tồn tại hoặc đã bị khóa.")
    return loc


def _assert_destination_free(
    db: Session,
    cart: ItemStock,
    new_loc: Location,
) -> None:
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
            f"Vị trí '{new_loc_display}' đang có Rack '{occupying_cart.container_code}' đỗ. "
            f"Vui lòng chọn vị trí trống."
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
            f"Vị trí '{new_loc_display}' đang có AMR nhiệm vụ '{incoming_task.mission_code}' "
            f"chở hàng tới. Vui lòng chọn vị trí khác hoặc thử lại sau."
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
            f"Vị trí '{new_loc_display}' đang có yêu cầu '{waiting_dest_req.request_code}' "
            f"({waiting_dest_req.status}). Vui lòng chọn vị trí khác hoặc hủy yêu cầu trước."
        )


def _fleet_move_container(
    db: Session,
    cart: ItemStock,
    old_loc: Optional[Location],
    new_loc: Location,
) -> None:
    c_code = (cart.container_code or "").strip()
    old_loc_display = (old_loc.location_name or old_loc.location_code) if old_loc else "Chưa rõ"
    new_loc_display = new_loc.location_name or new_loc.location_code

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
                "Sync-bypass Rack '%s' thất bại containerOut tại '%s': %s",
                c_code,
                old_loc.location_code,
                out_err,
                exc_info=True,
            )
            raise ValueError(
                f"Không thể gỡ Rack '{c_code}' khỏi vị trí cũ '{old_loc_display}' "
                f"trên KUKA Fleet (containerOut): {out_err}"
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
                rollback_note = (
                    f" (Đã khôi phục Rack về vị trí cũ '{old_loc_display}' trên KUKA Fleet)."
                )
            except Exception as restore_err:
                logger.error(
                    "Khôi phục Rack '%s' về '%s' trên Fleet thất bại: %s",
                    c_code,
                    old_loc.location_code,
                    restore_err,
                )
                rollback_note = (
                    f" (Cảnh báo: không khôi phục được về '{old_loc_display}' trên Fleet: "
                    f"{restore_err})."
                )
        db.commit()
        raise ValueError(
            f"KUKA Fleet từ chối đặt Rack '{c_code}' vào '{new_loc_display}' "
            f"(containerIn): {in_err}{rollback_note}"
        ) from in_err


def _add_production_record(
    db: Session,
    *,
    cart: ItemStock,
    stage_level: int,
    location_id: Optional[int],
    machine_code: Optional[str],
    operator_id: Optional[int],
    notes: str,
) -> ProductionRecord:
    resolved_location_id = location_id if location_id is not None else cart.location_id
    if not resolved_location_id:
        raise ValueError("Thiếu location_id để ghi production_record.")
    if not cart.item_id:
        raise ValueError("Rack chưa gắn Model (item_id) — không thể ghi production_record.")
    record = ProductionRecord(
        container_id=cart.id,
        container_code=cart.container_code,
        item_id=cart.item_id,
        stage_level=stage_level,
        location_id=resolved_location_id,
        machine_code=machine_code,
        operator_id=operator_id,
        notes=notes,
    )
    db.add(record)
    return record


def _scan_queues_safe(db: Session) -> None:
    try:
        dispatch_service.try_resolve_waiting_slot_queue(db)
        dispatch_service.try_resolve_waiting_cart_queue(db)
    except Exception as exc:
        logger.warning("Queue scan after sync-bypass failed: %s", exc)


def _derive_stage_from_location(
    *,
    location: Location,
    route_ctx: Optional[dict[str, Any]],
    item_label: str,
) -> int:
    """
    Suy current_stage_level từ vị trí đích + route:
    - RAW_MATERIAL → 0
    - CNC_SLOT → stage S của máy trong route_step_machine (max nếu máy gắn nhiều bước)
    - WASHING_SLOT → stage_level của bước is_final_cnc_step=True
    Node/máy ngoài route → ValueError.
    """
    loc_type = location.location_type
    loc_display = location.location_name or location.location_code

    if loc_type == "RAW_MATERIAL":
        return 0

    if not route_ctx:
        raise ValueError(
            f"Model '{item_label}' chưa có Quy trình active — không suy được stage từ vị trí '{loc_display}'."
        )

    if loc_type == "WASHING_SLOT":
        final_stage = int(route_ctx.get("final_stage") or 0)
        if final_stage <= 0:
            raise ValueError(
                f"Quy trình của '{item_label}' chưa có bước CNC cuối (is_final_cnc_step=true)."
            )
        return final_stage

    if loc_type == "CNC_SLOT":
        machine_id = location.machine_id
        machine_stages: dict[int, set[int]] = route_ctx.get("machine_stages") or {}
        if not machine_id or machine_id not in machine_stages:
            raise ValueError(
                f"Vị trí/node '{loc_display}' không thuộc Quy trình của model '{item_label}'. "
                f"Chỉ chọn máy có trong route_step_machine."
            )
        stages = machine_stages[machine_id]
        if not stages:
            raise ValueError(
                f"Vị trí/node '{loc_display}' không thuộc Quy trình của model '{item_label}'."
            )
        return max(stages)

    raise ValueError(
        f"Loại vị trí '{loc_type}' tại '{loc_display}' không hợp lệ cho bypass "
        f"(chỉ RAW_MATERIAL / CNC_SLOT / WASHING_SLOT)."
    )


def sync_physical_bypass(
    db: Session,
    *,
    rack_id: int,
    new_location_id: int,
    note: str,
    new_stage_level: Optional[int] = None,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    W1 / CNC→CNC: xe đã đứng đúng chỗ thực tế.
    Đổi location + stage (suy từ node/route) + Fleet sync + production_record(note).
    """
    clean_note = _require_note(note)

    cart = _load_rack_for_update(db, rack_id)
    _ensure_rack_modifiable(db, cart, "đồng bộ bypass", require_relocatable=True)

    new_loc = _load_active_location(db, new_location_id)
    new_loc_display = new_loc.location_name or new_loc.location_code
    item_label = cart.item.name if cart.item else f"Model ID={cart.item_id}"

    route_ctx_map = _build_route_context_by_item(db, {cart.item_id} if cart.item_id else set())
    route_ctx = route_ctx_map.get(cart.item_id) if cart.item_id else None

    derived_stage = _derive_stage_from_location(
        location=new_loc,
        route_ctx=route_ctx,
        item_label=item_label,
    )
    if new_stage_level is not None and int(new_stage_level) != derived_stage:
        raise ValueError(
            f"Stage gửi lên (Lv {new_stage_level}) không khớp vị trí '{new_loc_display}' "
            f"(route suy ra Lv {derived_stage})."
        )
    resolved_stage = derived_stage

    if cart.location_id == new_location_id and int(cart.current_stage_level or 0) == resolved_stage:
        raise ValueError("Vị trí và stage mới trùng với trạng thái hiện tại của Rack.")

    previous_stage = int(cart.current_stage_level or 0)
    cart.current_stage_level = resolved_stage

    is_valid_dest, dest_err = _validate_location_for_cart(cart, new_loc, route_ctx)
    if not is_valid_dest:
        cart.current_stage_level = previous_stage
        raise ValueError(dest_err)

    if cart.location_id != new_location_id:
        _assert_destination_free(db, cart, new_loc)

    old_loc_id = cart.location_id
    old_loc = db.query(Location).filter(Location.id == old_loc_id).first() if old_loc_id else None
    c_code = (cart.container_code or "").strip()
    bind_context(container_code=c_code, station_code=new_loc.location_code)

    if cart.location_id != new_location_id:
        _fleet_move_container(db, cart, old_loc, new_loc)
        cart.location_id = new_loc.id
        cart.destination_location_id = None
        cart.fleet_registered = True
    elif not cart.fleet_registered and new_loc.location_code:
        try:
            dispatch_service.fleet_container_in(
                location_code=new_loc.location_code,
                container_code=c_code,
                is_new=False,
                db=db,
            )
            cart.fleet_registered = True
        except Exception as in_err:
            cart.current_stage_level = previous_stage
            db.commit()
            raise ValueError(
                f"KUKA Fleet từ chối đăng ký Rack '{c_code}' tại '{new_loc_display}': {in_err}"
            ) from in_err

    machine_code = new_loc.machine.machine_code if getattr(new_loc, "machine", None) else None
    audit_note = f"[SYNC_PHYSICAL bypass] {clean_note}"
    _add_production_record(
        db,
        cart=cart,
        stage_level=resolved_stage,
        location_id=new_loc.id,
        machine_code=machine_code,
        operator_id=operator_id,
        notes=audit_note,
    )

    loc_ids = sorted({int(lid) for lid in (old_loc_id, new_loc.id) if lid is not None})
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[operator_id],
    )

    db.commit()
    db.refresh(cart)
    _scan_queues_safe(db)

    publish_event(
        "floor.changed",
        {
            "reason": "rack_sync_bypass",
            "mode": "SYNC_PHYSICAL",
            "location_ids": loc_ids,
            "container_code": c_code,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    return {
        "success": True,
        "message": (
            f"Đã đồng bộ Rack '{c_code}' → '{new_loc_display}' "
            f"(stage Lv {resolved_stage}) và ghi production_record."
        ),
        "mode": "SYNC_PHYSICAL",
        "rack": serialize_rack(cart),
    }


def dispatch_to_wash_bypass(
    db: Session,
    *,
    rack_id: int,
    note: str,
    preferred_wash_location_id: Optional[int] = None,
    new_stage_level: Optional[int] = None,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    W2: xe còn tại CNC cuối — stage = final is_final_cnc_step,
    tạo MOVE_TO_WASH (AMR) hoặc xếp WAITING_SLOT nếu rửa đầy.
    """
    clean_note = _require_note(note)

    cart = _load_rack_for_update(db, rack_id)
    _ensure_rack_modifiable(db, cart, "điều xe sang rửa (bypass)", require_relocatable=True)

    if not cart.location_id:
        raise ValueError("Rack chưa có vị trí hiện tại — không thể điều AMR sang khu rửa.")

    current_loc = (
        db.query(Location)
        .options(joinedload(Location.machine))
        .filter(Location.id == cart.location_id)
        .first()
    )
    if not current_loc:
        raise ValueError("Vị trí hiện tại của Rack không hợp lệ.")
    if current_loc.location_type == "WASHING_SLOT":
        raise ValueError(
            "Rack đã nằm tại Khu Tẩy Rửa. Hãy dùng mode SYNC_PHYSICAL nếu chỉ cần đồng bộ dữ liệu, "
            "hoặc dùng PDA 'Giải phóng slot' để trả xe rỗng."
        )
    if current_loc.location_type != "CNC_SLOT":
        raise ValueError(
            f"DISPATCH_TO_WASH chỉ áp dụng khi Rack đang ở CNC_SLOT "
            f"(hiện tại: {current_loc.location_type})."
        )

    item_label = cart.item.name if cart.item else f"Model ID={cart.item_id}"
    route_ctx_map = _build_route_context_by_item(db, {cart.item_id} if cart.item_id else set())
    route_ctx = route_ctx_map.get(cart.item_id) if cart.item_id else None
    final_stage = int((route_ctx or {}).get("final_stage") or 0)
    if final_stage <= 0:
        raise ValueError(
            f"Model '{item_label}' chưa có bước CNC cuối (is_final_cnc_step=true) để đi rửa."
        )
    if new_stage_level is not None and int(new_stage_level) != final_stage:
        raise ValueError(
            f"Stage gửi lên (Lv {new_stage_level}) không khớp bước CNC cuối (Lv {final_stage})."
        )
    resolved_stage = final_stage

    previous_stage = int(cart.current_stage_level or 0)
    cart.current_stage_level = resolved_stage

    machine_code = (
        current_loc.machine.machine_code if getattr(current_loc, "machine", None) else None
    )
    audit_note = f"[DISPATCH_TO_WASH bypass] {clean_note}"
    _add_production_record(
        db,
        cart=cart,
        stage_level=resolved_stage,
        location_id=cart.location_id,
        machine_code=machine_code,
        operator_id=operator_id,
        notes=audit_note,
    )

    wash_slot: Optional[Location] = None
    if preferred_wash_location_id:
        preferred = _load_active_location(db, preferred_wash_location_id)
        if preferred.location_type != "WASHING_SLOT":
            cart.current_stage_level = previous_stage
            raise ValueError(
                f"Vị trí ưu tiên phải là WASHING_SLOT (nhận được: {preferred.location_type})."
            )
        # Wash thuộc mọi route có final step — không map qua route_step_machine
        try:
            _assert_destination_free(db, cart, preferred)
            wash_slot = preferred
        except ValueError:
            wash_slot = None

    if wash_slot is None:
        wash_slot = dispatch_service.selector.find_available_slot_to_wash(db)

    c_code = (cart.container_code or "").strip()
    bind_context(container_code=c_code, station_code=current_loc.location_code)
    req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"

    if wash_slot:
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="MOVE_TO_WASH",
            item_id=cart.item_id,
            source_location_id=cart.location_id,
            destination_location_id=wash_slot.id,
            container_id=cart.id,
            required_stage_level=resolved_stage,
            status="pending",
            priority=5,
            created_by=operator_id,
        )
        db.add(transport_req)
        db.flush()
        try:
            dispatch_service._lock_cart_and_dispatch_fleet_task(
                db=db,
                transport_req=transport_req,
                cart=cart,
                pickup_location_id=cart.location_id,
                dropoff_location_id=wash_slot.id,
            )
        except Exception:
            cart.current_stage_level = previous_stage
            db.commit()
            raise

        action = "DISPATCHED_TO_WASHING"
        wash_display = wash_slot.location_name or wash_slot.location_code
        message = (
            f"Đã bypass hoàn thành CNC cuối cho Rack '{c_code}' "
            f"và điều AMR sang '{wash_display}'."
        )
        loc_ids = sorted(
            {int(lid) for lid in (current_loc.id, wash_slot.id) if lid is not None}
        )
    else:
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="MOVE_TO_WASH",
            item_id=cart.item_id,
            source_location_id=cart.location_id,
            destination_location_id=cart.location_id,
            container_id=cart.id,
            required_stage_level=resolved_stage,
            status="queued_for_slot",
            priority=5,
            created_by=operator_id,
        )
        db.add(transport_req)
        db.flush()
        dispatch_service.queue_service.enqueue(
            db=db,
            request_id=transport_req.id,
            queue_type="WAITING_SLOT",
            target_stage_level=99,
            priority=5,
        )
        action = "QUEUED_FOR_WASHING_SLOT"
        message = (
            f"Đã bypass hoàn thành CNC cuối cho Rack '{c_code}' nhưng chưa có ô rửa trống — "
            f"đã xếp WAITING_SLOT."
        )
        loc_ids = [current_loc.id]

    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[operator_id],
    )
    db.commit()
    db.refresh(cart)

    if action == "QUEUED_FOR_WASHING_SLOT":
        _scan_queues_safe(db)

    publish_event(
        "floor.changed",
        {
            "reason": "rack_sync_bypass",
            "mode": "DISPATCH_TO_WASH",
            "action": action,
            "location_ids": loc_ids,
            "container_code": c_code,
            "request_code": transport_req.request_code,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    return {
        "success": True,
        "message": message,
        "mode": "DISPATCH_TO_WASH",
        "action": action,
        "request_code": transport_req.request_code,
        "rack": serialize_rack(cart),
    }


def sync_rack_bypass(
    db: Session,
    *,
    rack_id: int,
    mode: SyncBypassMode,
    note: str,
    location_id: Optional[int] = None,
    new_stage_level: Optional[int] = None,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    if mode == "SYNC_PHYSICAL":
        if not location_id:
            raise ValueError("SYNC_PHYSICAL yêu cầu location_id (vị trí thực tế mới).")
        return sync_physical_bypass(
            db,
            rack_id=rack_id,
            new_location_id=location_id,
            note=note,
            new_stage_level=new_stage_level,
            operator_id=operator_id,
        )
    if mode == "DISPATCH_TO_WASH":
        return dispatch_to_wash_bypass(
            db,
            rack_id=rack_id,
            note=note,
            preferred_wash_location_id=location_id,
            new_stage_level=new_stage_level,
            operator_id=operator_id,
        )
    raise ValueError(f"mode không hợp lệ: {mode}")
