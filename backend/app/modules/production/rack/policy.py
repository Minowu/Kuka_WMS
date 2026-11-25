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
    Trả về `{item_id: {route_id, max_stage, final_stage, machine_stages}}`.
    `final_stage` = stage_level của bước `is_final_cnc_step=True` (fallback max_stage).
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
        final_stages = [st.stage_level for st in steps if st.is_final_cnc_step]
        final_stage = max(final_stages) if final_stages else max_stage
        machine_stages: dict[int, set[int]] = {}
        for st in steps:
            for link in st.allowed_machine_links or []:
                if link.machine_id is not None:
                    machine_stages.setdefault(link.machine_id, set()).add(st.stage_level)
        result[route.item_id] = {
            "route_id": route.id,
            "max_stage": max_stage,
            "final_stage": final_stage,
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
    final_stage = int(route_ctx.get("final_stage") or max_stage or 0)
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
        if final_stage <= 0 or cart_level < final_stage:
            return (
                False,
                f"Rack mới ở công đoạn Lv {cart_level} (chưa hoàn thành bước CNC cuối Lv {final_stage} "
                f"của Model '{item_name}'), không thể chuyển thẳng vào Khu Tẩy Rửa '{loc_display}'.",
            )
        return True, None

    return False, f"Loại vị trí '{loc_type}' tại '{loc_display}' không hợp lệ để đặt Rack."

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
