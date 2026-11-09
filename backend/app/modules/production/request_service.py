"""Business logic for Admin Transport Request & Queue Management (List & Cancel)."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import bind_context, get_logger
from app.modules.production.dispatch_service import dispatch_service
from app.modules.production.production_models import (
    FleetTask,
    ProductionRoute,
    RouteStep,
    TransportQueue,
    TransportRequest,
)
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.dispatch")

ACTIVE_TASK_STATUSES = ("created", "pending_submit", "submitting", "sent", "dispatched", "in_progress")
ACTIVE_REQUEST_STATUSES = ("pending", "queued_for_cart", "queued_for_slot", "in_progress")


def serialize_transport_request(
    req: TransportRequest,
    latest_queue: Optional[TransportQueue] = None,
    latest_task: Optional[FleetTask] = None,
) -> dict[str, Any]:
    src = req.source_location
    dst = req.destination_location
    item = req.item
    cart = req.container or (latest_task.container if latest_task else None)
    creator = req.creator

    src_machine = src.machine.machine_code if (src and getattr(src, "machine", None)) else None
    dst_machine = dst.machine.machine_code if (dst and getattr(dst, "machine", None)) else None

    can_cancel = req.status in ACTIVE_REQUEST_STATUSES
    cancel_block_reason = None
    if not can_cancel:
        cancel_block_reason = f"Yêu cầu đã kết thúc ở trạng thái '{req.status}', không cần hủy."

    return {
        "id": req.id,
        "request_code": req.request_code,
        "request_type": req.request_type,
        "status": req.status,
        "priority": int(req.priority or 10),
        "item_id": req.item_id,
        "item_sku": item.sku if item else None,
        "item_name": item.name if item else None,
        "required_stage_level": int(req.required_stage_level or 0),
        "target_stage_level": latest_queue.target_stage_level if latest_queue else None,
        "container_id": cart.id if cart else req.container_id,
        "container_code": cart.container_code if cart else (latest_task.container_code if latest_task else None),
        "source_location_id": req.source_location_id,
        "source_location_code": src.location_code if src else None,
        "source_location_name": (src.location_name or src.location_code) if src else None,
        "source_location_label": src.location_label if src else None,
        "source_location_type": src.location_type if src else None,
        "source_machine_code": src_machine,
        "destination_location_id": req.destination_location_id,
        "destination_location_code": dst.location_code if dst else None,
        "destination_location_name": (dst.location_name or dst.location_code) if dst else None,
        "destination_location_label": dst.location_label if dst else None,
        "destination_location_type": dst.location_type if dst else None,
        "destination_machine_code": dst_machine,
        "queue_type": latest_queue.queue_type if latest_queue else None,
        "queue_status": latest_queue.status if latest_queue else None,
        "mission_code": latest_task.mission_code if latest_task else None,
        "fleet_task_status": latest_task.status if latest_task else None,
        "robot_id": latest_task.robot_id if latest_task else None,
        "created_by": req.created_by,
        "created_by_username": creator.username if creator else None,
        "created_by_full_name": creator.full_name if creator else None,
        "can_cancel": can_cancel,
        "cancel_block_reason": cancel_block_reason,
        "created_at": req.created_at,
        "completed_at": req.completed_at,
    }


def list_transport_requests(
    db: Session,
    include_history: bool = False,
    search: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """
    Lấy danh sách các yêu cầu vận chuyển (`TransportRequest`) kèm thông tin máy CNC, vị trí nguồn/đích,
    hàng đợi (`TransportQueue`), nhiệm vụ AMR (`FleetTask`) và người tạo để Admin dễ dàng kiểm soát & hủy.
    """
    query = (
        db.query(TransportRequest)
        .options(
            joinedload(TransportRequest.item),
            joinedload(TransportRequest.container),
            joinedload(TransportRequest.source_location).joinedload(Location.machine),
            joinedload(TransportRequest.destination_location).joinedload(Location.machine),
            joinedload(TransportRequest.creator),
        )
    )
    if not include_history:
        query = query.filter(TransportRequest.status.in_(ACTIVE_REQUEST_STATUSES))

    reqs = (
        query.order_by(
            TransportRequest.id.desc(),
        )
        .limit(limit)
        .all()
    )
    if not reqs:
        return []

    req_ids = [r.id for r in reqs]

    queues = (
        db.query(TransportQueue)
        .filter(TransportQueue.request_id.in_(req_ids))
        .order_by(TransportQueue.id.desc())
        .all()
    )
    queue_by_req_id: dict[int, TransportQueue] = {}
    for q in queues:
        if q.request_id not in queue_by_req_id:
            queue_by_req_id[q.request_id] = q

    tasks = (
        db.query(FleetTask)
        .options(joinedload(FleetTask.container))
        .filter(FleetTask.request_id.in_(req_ids))
        .order_by(FleetTask.id.desc())
        .all()
    )
    task_by_req_id: dict[int, FleetTask] = {}
    for t in tasks:
        if t.request_id and t.request_id not in task_by_req_id:
            task_by_req_id[t.request_id] = t

    items = [
        serialize_transport_request(
            r,
            latest_queue=queue_by_req_id.get(r.id),
            latest_task=task_by_req_id.get(r.id),
        )
        for r in reqs
    ]

    if search and search.strip():
        kw = search.strip().lower()
        items = [
            it
            for it in items
            if kw in (it["request_code"] or "").lower()
            or kw in (it["container_code"] or "").lower()
            or kw in (it["mission_code"] or "").lower()
            or kw in (it["item_sku"] or "").lower()
            or kw in (it["item_name"] or "").lower()
            or kw in (it["source_location_name"] or "").lower()
            or kw in (it["source_location_code"] or "").lower()
            or kw in (it["source_machine_code"] or "").lower()
            or kw in (it["destination_location_name"] or "").lower()
            or kw in (it["destination_location_code"] or "").lower()
            or kw in (it["destination_machine_code"] or "").lower()
            or kw in (it["created_by_username"] or "").lower()
        ]
    return items


def cancel_transport_request_by_admin(
    db: Session,
    request_id: int,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Hủy yêu cầu vận chuyển (`TransportRequest`) bởi Admin:
    1. Đóng toàn bộ bản ghi `TransportQueue` (`status = 'CANCELLED'`) để hệ thống không tự gọi lại.
    2. Nếu yêu cầu đã sinh `FleetTask` đang hoạt động:
       - Gửi lệnh `/amr/missionCancel` sang KUKA Fleet nếu nhiệm vụ đã gửi sang Fleet (`sent`, `dispatched`, `in_progress`).
       - Đánh dấu `FleetTask.status = 'cancelled'`.
    3. Mở khóa xe phôi (`ItemStock.is_locked = False`), khôi phục `current_stage_level` (nếu là lệnh đi Rửa)
       hoặc `status = 'available'` (nếu là lệnh trả xe rỗng từ khu Rửa).
    4. Phát sự kiện WebSocket `floor.changed` tới công nhân tại vị trí nguồn/đích
       để màn hình PDA của Operator tự động cập nhật ngay lập tức!
    """
    req = (
        db.query(TransportRequest)
        .options(
            joinedload(TransportRequest.item),
            joinedload(TransportRequest.container),
            joinedload(TransportRequest.source_location).joinedload(Location.machine),
            joinedload(TransportRequest.destination_location).joinedload(Location.machine),
            joinedload(TransportRequest.creator),
        )
        .filter(TransportRequest.id == request_id)
        .with_for_update(of=TransportRequest)
        .first()
    )
    if not req:
        raise ValueError(f"Không tìm thấy yêu cầu vận chuyển (ID={request_id}).")

    if req.status not in ACTIVE_REQUEST_STATUSES:
        raise ValueError(
            f"Yêu cầu '{req.request_code}' đã ở trạng thái '{req.status}', không thể hủy."
        )

    bind_context(transport_request_id=req.id)
    now = datetime.now(timezone.utc)

    # 1. Hủy tất cả bản ghi hàng đợi TransportQueue của request này
    pending_queues = (
        db.query(TransportQueue)
        .filter(TransportQueue.request_id == req.id)
        .order_by(TransportQueue.id.desc())
        .all()
    )
    latest_queue = pending_queues[0] if pending_queues else None
    for q in pending_queues:
        if q.status == "PENDING":
            q.status = "CANCELLED"
            q.resolved_at = now

    # 2. Kiểm tra và hủy FleetTask đang chạy (nếu có)
    active_tasks = (
        db.query(FleetTask)
        .options(joinedload(FleetTask.container))
        .filter(
            FleetTask.request_id == req.id,
            FleetTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(FleetTask.id.desc())
        .all()
    )
    latest_task = active_tasks[0] if active_tasks else None
    fleet_cancel_note = ""

    for task in active_tasks:
        if task.mission_code and task.status in ("sent", "dispatched", "in_progress"):
            try:
                dispatch_service.fleet_client.fleet_cancel_task(task.mission_code)
                fleet_cancel_note = f" (Đã gửi lệnh hủy missionCancel '{task.mission_code}' sang KUKA Fleet)."
            except Exception as cancel_err:
                logger.warning(
                    "Gửi missionCancel cho '%s' khi Admin hủy request '%s' báo lỗi (vẫn tiếp tục hủy trong WMS): %s",
                    task.mission_code,
                    req.request_code,
                    cancel_err,
                )
                fleet_cancel_note = f" (Lưu ý: Lệnh hủy bên KUKA Fleet phản hồi: {cancel_err})."

        task.status = "cancelled"
        task.error_message = f"Admin đã hủy yêu cầu '{req.request_code}'"
        task.updated_at = now

    # 3. Mở khóa xe phôi và khôi phục trạng thái nghiệp vụ cho Operator PDA
    cart = req.container or (latest_task.container if latest_task else None)
    if cart:
        task_mission_codes = {t.mission_code for t in active_tasks if t.mission_code}
        if not cart.locked_by_mission_code or cart.locked_by_mission_code in task_mission_codes:
            cart.is_locked = False
            cart.locked_by_mission_code = None
            cart.destination_location_id = None

        # Nếu là lệnh từ máy CNC cuối đi Rửa -> Khôi phục current_stage_level về bước trước để nút 'Hoàn thành' hiện lại trên PDA
        if req.request_type in ("MOVE_TO_WASH", "SEND_TO_WASH"):
            req_stage = req.required_stage_level or 0
            if req_stage > 0 and (cart.current_stage_level or 0) >= req_stage:
                prev_step = (
                    db.query(RouteStep.stage_level)
                    .join(ProductionRoute, RouteStep.route_id == ProductionRoute.id)
                    .filter(
                        ProductionRoute.item_id == cart.item_id,
                        RouteStep.stage_level < req_stage,
                    )
                    .order_by(RouteStep.stage_level.desc())
                    .first()
                )
                cart.current_stage_level = prev_step[0] if prev_step else max(0, req_stage - 1)

        # Nếu là lệnh trả xe rỗng từ khu Rửa -> Đảm bảo status = 'available' để xe không biến mất khỏi PDA khu Rửa
        elif req.request_type == "RETURN_EMPTY_CART":
            if cart.status == "empty":
                cart.status = "available"

    req.status = "cancelled"
    req.completed_at = now

    raw_loc_ids = [
        req.source_location_id,
        req.destination_location_id,
        latest_task.pickup_location_id if latest_task else None,
        latest_task.dropoff_location_id if latest_task else None,
        cart.location_id if cart else None,
    ]
    loc_ids = sorted({int(lid) for lid in raw_loc_ids if lid is not None})
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[req.created_by, operator_id],
    )

    db.commit()
    db.refresh(req)

    # Nếu vừa mở khóa xe hoặc giải phóng slot đích, thử quét hàng đợi cho các yêu cầu khác
    try:
        dispatch_service.try_resolve_waiting_slot_queue(db)
        dispatch_service.try_resolve_waiting_cart_queue(db)
    except Exception as exc:
        logger.warning("Queue scan after request cancellation failed: %s", exc)

    # Phát sự kiện WebSocket để màn hình PDA của Operator tại trạm đó tự động cập nhật ngay lập tức!
    publish_event(
        "floor.changed",
        {
            "reason": "request_cancelled_by_admin",
            "request_code": req.request_code,
            "location_ids": loc_ids,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    dest_display = (
        (req.destination_location.location_name or req.destination_location.location_code)
        if req.destination_location
        else (req.source_location.location_name or req.source_location.location_code if req.source_location else "")
    )
    return {
        "success": True,
        "message": f"Đã hủy yêu cầu '{req.request_code}' ({dest_display}) thành công và cập nhật tới màn hình Operator.{fleet_cancel_note}",
        "request": serialize_transport_request(req, latest_queue=latest_queue, latest_task=latest_task),
    }
