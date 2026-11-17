"""Fleet task fail/cancel release helpers."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.production.production_models import (
    FleetTask,
    ProductionRoute,
    RouteStep,
    TransportQueue,
)
from app.socket.event_bus import resolve_location_recipient_user_ids, schedule_event_after_commit


def fail_and_release(
    db: Session,
    task: FleetTask,
    reason: str,
    *,
    is_cancelled: bool = False,
) -> FleetTask:
    """
    Đánh dấu `FleetTask` là `failed` hoặc `cancelled` (đảm bảo tính bất biến/idempotent),
    mở khóa xe phôi `ItemStock`, khôi phục an toàn trạng thái nghiệp vụ cho cả 4 luồng sản xuất,
    và xếp hàng phát sự kiện WebSocket `fleet.task_failed` + `floor.changed` ngay sau khi `db.commit()`:
    1. Mở khóa xe `task.container` (`is_locked = False`, xóa `locked_by_mission_code` và `destination_location_id`).
    2. Nếu `is_cancelled=True` (nhiệm vụ bị hủy chủ động từ KUKA Fleet hoặc Admin):
       - Đóng toàn bộ bản ghi `TransportQueue` (`status = 'CANCELLED'`) để Celery không tự điều xe lại.
       - Đưa `TransportRequest.status = 'cancelled'` để màn hình PDA của Operator về trạng thái sẵn sàng ngay.
    3. Nếu `is_cancelled=False` (lỗi mạng/lỗi Fleet từ chối) và `task.request` xuất phát từ `TransportQueue`,
       mở lại bản ghi hàng đợi về trạng thái `PENDING` để yêu cầu không bao giờ bị mất khi Fleet lỗi tạm thời.
    4. Nếu `task.request` là `MOVE_TO_WASH` / `SEND_TO_WASH` (từ máy CNC cuối đi Rửa), khôi phục
       `cart.current_stage_level` về công đoạn trước đó để nút 'Hoàn thành công đoạn' hiện lại trên PDA.
    5. Nếu `task.request` là `RETURN_EMPTY_CART` (từ khu Rửa trả xe rỗng), khôi phục
       `cart.status = 'available'` để chiếc xe không bị biến mất khỏi màn hình PDA khu Rửa.
    """
    now = datetime.now(timezone.utc)
    task.status = "cancelled" if is_cancelled else "failed"
    task.error_message = reason
    task.updated_at = now

    cart = task.container
    if cart:
        if not cart.locked_by_mission_code or cart.locked_by_mission_code == task.mission_code:
            cart.is_locked = False
            cart.locked_by_mission_code = None
            cart.destination_location_id = None

    req = task.request
    req_type = req.request_type if req else None
    if req and req.status not in ("completed", "cancelled"):
        queue_entries = (
            db.query(TransportQueue)
            .filter(TransportQueue.request_id == req.id)
            .order_by(TransportQueue.id.desc())
            .all()
        )
        queue_entry = queue_entries[0] if queue_entries else None

        if is_cancelled:
            # Khi hủy chủ động (CANCELED), đóng toàn bộ hàng đợi để hệ thống không tự gọi lại
            # và giải phóng màn hình PDA của Operator ngay lập tức!
            for q in queue_entries:
                if q.status in ("PENDING", "PROCESSING"):
                    q.status = "CANCELLED"
                    q.resolved_at = now
            req.status = "cancelled"
            req.completed_at = now
        elif queue_entry:
            # Nếu lỗi kỹ thuật (FAILED) và yêu cầu xuất phát từ Hàng đợi tự động, mở lại PENDING để chu kỳ quét sau thử lại
            queue_entry.status = "PENDING"
            queue_entry.resolved_at = None
            if queue_entry.queue_type == "WAITING_CART":
                req.status = "queued_for_cart"
                req.container_id = None
                req.source_location_id = None
            else:
                req.status = "queued_for_slot"
        else:
            req.status = "failed"

        # Khi lệnh dừng hẳn (failed hoặc cancelled mà không đẩy lại vào queue),
        # khôi phục trạng thái nghiệp vụ trên xe phôi để PDA trạm nguồn bấm lại được!
        if req.status in ("failed", "cancelled") and cart:
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
            elif req.request_type == "RETURN_EMPTY_CART":
                if cart.status == "empty":
                    cart.status = "available"

    db.flush()

    # Xác định các vị trí liên quan và danh sách công nhân nhận thông báo qua WebSocket sau khi commit
    raw_loc_ids = [
        task.pickup_location_id,
        task.dropoff_location_id,
        req.source_location_id if req else None,
        req.destination_location_id if req else None,
        cart.location_id if cart else None,
    ]
    loc_ids = sorted({int(lid) for lid in raw_loc_ids if lid is not None})

    if req_type in ("MOVE_TO_WASH", "SEND_TO_WASH", "RETURN_EMPTY_CART"):
        primary_loc_id = (
            (req.source_location_id if req else None)
            or task.pickup_location_id
            or task.dropoff_location_id
        )
    else:
        primary_loc_id = (
            (req.destination_location_id if req else None)
            or task.dropoff_location_id
            or task.pickup_location_id
        )

    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[req.created_by if req else None],
    )

    m_code = task.mission_code or f"task-{task.id}"
    schedule_event_after_commit(
        db,
        dedup_key=f"fleet.task_failed:{m_code}",
        event_type="fleet.task_failed",
        payload={
            "mission_code": task.mission_code,
            "location_id": primary_loc_id,
            "location_ids": loc_ids,
            "container_code": task.container_code,
            "request_type": req_type,
            "message": reason,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )
    schedule_event_after_commit(
        db,
        dedup_key=f"floor.changed:fail:{m_code}",
        event_type="floor.changed",
        payload={
            "reason": "task_failed",
            "mission_code": task.mission_code,
            "location_ids": loc_ids,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    return task


