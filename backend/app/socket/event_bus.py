"""Bus sự kiện thời gian thực qua Redis Pub/Sub cho WebSocket (Bước S4 & S5 - Mục 1.8a, 1.8d)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Iterable, Optional

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.cache import get_redis
from app.core.logger import get_logger

logger = get_logger("main")

# Kênh Redis Pub/Sub dùng chung giữa FastAPI Backend và các Celery Workers
REDIS_EVENTS_CHANNEL = "wms:events"


def resolve_location_recipient_user_ids(
    db: Session,
    location_ids: Iterable[Optional[int]],
    extra_user_ids: Optional[Iterable[Optional[int]]] = None,
) -> list[int]:
    """
    Tính sẵn danh sách `user_id` cần nhận sự kiện WebSocket dựa trên:
    - Các công nhân được phân công phụ trách các vị trí `location_ids` trong bảng `UserLocation`.
    - Cộng thêm danh sách `extra_user_ids` (ví dụ: `created_by`, `operator_id` vừa bấm nút).

    Nhờ tính sẵn danh sách người nhận trước khi gửi lên Redis, tiến trình Subscriber
    ở `ws_manager` hoàn toàn KHÔNG cần truy vấn lại Database khi phân phối tin nhắn.
    """
    from app.modules.production.production_models import UserLocation

    recipients: set[int] = set()
    if extra_user_ids:
        for uid in extra_user_ids:
            if uid is not None:
                try:
                    recipients.add(int(uid))
                except (TypeError, ValueError):
                    pass

    valid_loc_ids = sorted({int(lid) for lid in (location_ids or []) if lid is not None})
    if valid_loc_ids:
        try:
            rows = (
                db.query(UserLocation.user_id)
                .filter(UserLocation.location_id.in_(valid_loc_ids))
                .all()
            )
            for (uid,) in rows:
                if uid is not None:
                    recipients.add(int(uid))
        except Exception as exc:
            logger.warning("Không thể truy vấn UserLocation cho location_ids=%s: %s", valid_loc_ids, exc)

    return sorted(recipients)


def publish_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    user_ids: Optional[Iterable[Optional[int]]] = None,
    admins: bool = True,
) -> bool:
    """
    Phát sự kiện thời gian thực (`floor.changed`, `fleet.task_failed`, ...) qua Redis Pub/Sub (`wms:events`).
    - Luôn được gọi SAU KHI `db.commit()` thành công.
    - Bọc `try/except` toàn diện: nếu Redis gặp sự cố tạm thời thì chỉ ghi log cảnh báo,
      TUYỆT ĐỐI KHÔNG bao giờ ném ngoại lệ làm hỏng giao dịch nghiệp vụ sản xuất.
    """
    clean_user_ids: list[int] = []
    if user_ids is not None:
        clean_user_ids = sorted({int(uid) for uid in user_ids if uid is not None})

    envelope = {
        "type": event_type,
        "payload": payload or {},
        "targets": {
            "user_ids": clean_user_ids,
            "admins": bool(admins),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        raw_message = json.dumps(envelope, default=str)
        client = get_redis()
        client.publish(REDIS_EVENTS_CHANNEL, raw_message)
        return True
    except Exception as exc:
        logger.warning(
            "Không thể phát sự kiện WebSocket '%s' qua Redis Pub/Sub (nghiệp vụ vẫn tiếp tục bình thường): %s",
            event_type,
            exc,
        )
        return False


def _flush_ws_events_after_commit(session: Session, *args: Any, **kwargs: Any) -> None:
    """Hook tự động chạy ngay sau khi `session.commit()` hoàn tất thành công."""
    pending: dict[str, dict[str, Any]] = session.info.pop("_ws_after_commit_queue", {})
    for item in pending.values():
        publish_event(
            item["event_type"],
            item["payload"],
            user_ids=item["user_ids"],
            admins=item["admins"],
        )


def _clear_ws_events_after_rollback(session: Session, *args: Any, **kwargs: Any) -> None:
    """Xóa bỏ các sự kiện chờ phát nếu giao dịch DB bị rollback."""
    session.info.pop("_ws_after_commit_queue", None)


def schedule_event_after_commit(
    db: Session,
    dedup_key: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    user_ids: Optional[Iterable[Optional[int]]] = None,
    admins: bool = True,
) -> None:
    """
    Xếp hàng sự kiện WebSocket để tự động gọi `publish_event` NGAY SAU KHI `db.commit()` thành công.
    Nếu giao dịch bị rollback thì sự kiện tự động bị hủy bỏ.
    Dùng `dedup_key` để đảm bảo tính bất biến (idempotent) nếu hàm nghiệp vụ như `fail_and_release`
    được gọi lặp lại nhiều lần trong cùng một giao dịch.
    """
    if not db.info.get("_ws_listener_registered"):
        event.listen(db, "after_commit", _flush_ws_events_after_commit)
        event.listen(db, "after_rollback", _clear_ws_events_after_rollback)
        event.listen(db, "after_soft_rollback", _clear_ws_events_after_rollback)
        db.info["_ws_listener_registered"] = True

    queue: dict[str, dict[str, Any]] = db.info.setdefault("_ws_after_commit_queue", {})
    clean_user_ids = sorted({int(uid) for uid in (user_ids or []) if uid is not None})
    if dedup_key not in queue:
        queue[dedup_key] = {
            "event_type": event_type,
            "payload": payload or {},
            "user_ids": clean_user_ids,
            "admins": bool(admins),
        }
