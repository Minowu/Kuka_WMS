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


def complete_machining_stage_impl(
    core,
    db: Session,
    container_code: Optional[str] = None,
    location_id: Optional[int] = None,
    operator_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Operator confirms completion of CNC machining stage on rack."""
    cart: Optional[ItemStock] = None
    if container_code:
        cart = (
            db.query(ItemStock)
            .filter(ItemStock.container_code == container_code.strip(), ItemStock.is_active.is_(True))
            .first()
        )
    elif location_id:
        cart = (
            db.query(ItemStock)
            .filter(ItemStock.location_id == location_id, ItemStock.is_active.is_(True))
            .first()
        )

    if not cart:
        target_desc = f"mã '{container_code}'" if container_code else f"vị trí ID={location_id}"
        raise ValueError(f"Không tìm thấy khay phôi (ItemStock) đang hoạt động tại {target_desc}.")

    if cart.is_locked:
        raise ValueError(f"Khay phôi '{cart.container_code}' đang bị khóa bởi nhiệm vụ '{cart.locked_by_mission_code}'.")

    loc = db.query(Location).filter(Location.id == cart.location_id).first()
    if not loc:
        raise ValueError(f"Vị trí của khay phôi '{cart.container_code}' không hợp lệ.")

    station_code = loc.location_code
    machine_code = loc.machine.machine_code if getattr(loc, "machine", None) else None
    bind_context(
        container_code=cart.container_code,
        station_code=station_code,
        machine_code=machine_code,
    )

    _, target_stage, is_final_cnc = core.selector.get_stage_info_for_machine(db, loc, cart.item_id)
    current_stage = cart.current_stage_level or 0

    # Kiểm tra ngăn chặn cập nhật vượt cấp: Nếu xe đã đạt hoặc vượt stage của máy này -> Chặn lại
    if current_stage >= target_stage:
        raise ValueError(
            f"Khay phôi '{cart.container_code}' đã hoàn thành công đoạn Level {current_stage} "
            f"của máy này (yêu cầu Level {target_stage}). Vui lòng chờ AMR vận chuyển sang công đoạn tiếp theo."
        )

    completed_stage = target_stage
    previous_stage = cart.current_stage_level
    cart.current_stage_level = completed_stage

    record = ProductionRecord(
        container_id=cart.id,
        container_code=cart.container_code,
        item_id=cart.item_id,
        stage_level=completed_stage,
        location_id=cart.location_id,
        machine_code=machine_code,
        operator_id=operator_id,
        notes=notes,
    )
    db.add(record)

    if not is_final_cnc:
        recipient_user_ids = resolve_location_recipient_user_ids(
            db,
            [loc.id],
            extra_user_ids=[operator_id],
        )
        db.commit()
        core.queue_service.try_resolve_waiting_cart_queue(
            db,
            stage_level=completed_stage,
            lock_and_dispatch_fn=core.lock_cart_and_dispatch_fleet_task,
        )
        publish_event(
            "floor.changed",
            {
                "reason": "stage_completed",
                "location_ids": [loc.id],
                "container_code": cart.container_code,
            },
            user_ids=recipient_user_ids,
            admins=True,
        )
        return {
            "container_code": cart.container_code,
            "completed_stage_level": completed_stage,
            "is_final_cnc_step": False,
            "action": "WIP_AVAILABLE_FOR_NEXT_STAGE",
        }

    req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    wash_slot = core.selector.find_available_slot_to_wash(db)
    if wash_slot:
        logger.info(
            "Final CNC candidate decision: selected wash slot %s for cart %s",
            wash_slot.location_code,
            cart.container_code,
        )
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="MOVE_TO_WASH",
            item_id=cart.item_id,
            source_location_id=cart.location_id,
            destination_location_id=wash_slot.id,
            container_id=cart.id,
            required_stage_level=completed_stage,
            status="pending",
            priority=5,
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
            f"Final CNC completed for cart {cart.container_code}, moving to wash slot {wash_slot.location_code}",
        )

        try:
            core.lock_cart_and_dispatch_fleet_task(
                db=db,
                transport_req=transport_req,
                cart=cart,
                pickup_location_id=cart.location_id,
                dropoff_location_id=wash_slot.id,
            )
        except Exception as e:
            # Nếu gửi lệnh sang KUKA Fleet thất bại, khôi phục lại stage_level ban đầu
            # để nút 'Báo xong' trên PDA không bị ẩn mất vĩnh viễn!
            cart.current_stage_level = previous_stage
            db.commit()
            raise
        action_result = "DISPATCHED_TO_WASHING"
    else:
        logger.info(
            "Final CNC candidate decision: no wash slot available for cart %s; queuing request",
            cart.container_code,
        )
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="MOVE_TO_WASH",
            item_id=cart.item_id,
            source_location_id=cart.location_id,
            destination_location_id=cart.location_id,
            container_id=cart.id,
            required_stage_level=completed_stage,
            status="queued_for_slot",
            priority=5,
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
            f"No wash slot available for cart {cart.container_code}, enqueued in WAITING_SLOT",
        )
        core.queue_service.enqueue(
            db=db,
            request_id=transport_req.id,
            queue_type="WAITING_SLOT",
            target_stage_level=99,
            priority=5,
        )
        action_result = "QUEUED_FOR_WASHING_SLOT"

    loc_ids = sorted(
        {
            int(lid)
            for lid in (loc.id, wash_slot.id if wash_slot else None)
            if lid is not None
        }
    )
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[operator_id],
    )
    db.commit()

    if not wash_slot:
        publish_event(
            "floor.changed",
            {
                "reason": "stage_completed_queued_wash",
                "location_ids": loc_ids,
                "container_code": cart.container_code,
            },
            user_ids=recipient_user_ids,
            admins=True,
        )

    return {
        "container_code": cart.container_code,
        "completed_stage_level": completed_stage,
        "is_final_cnc_step": True,
        "action": action_result,
        "request_code": transport_req.request_code,
    }


def complete_machining_stage(
    core,
    db: Session,
    container_code: Optional[str] = None,
    location_id: Optional[int] = None,
    operator_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Facade → CompleteStageUseCase (single entry for DispatchCore)."""
    from app.application.production.use_cases.cnc_operations.complete_stage import (
        CompleteStageRequest,
    )
    from app.infrastructure.di.production_factory import build_complete_stage_use_case

    return build_complete_stage_use_case(db, core=core).execute(
        CompleteStageRequest(
            container_code=container_code,
            location_id=location_id,
            operator_id=operator_id,
            notes=notes,
        )
    )
