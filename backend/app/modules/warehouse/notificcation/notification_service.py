"""Notification stub service (decoupled from physical database table)."""

from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.modules.warehouse.notificcation.notification_schema import (
    NotificationCreate,
    NotificationListResponse,
    NotificationUpdate,
)


def count_unsolved_notifications(db: Session, warehouse_id: int) -> int:
    """Return 0 since notification table is decommissioned."""
    return 0


def list_notifications(
    db: Session,
    *,
    warehouse_id: int,
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
) -> NotificationListResponse:
    """Return empty list for frontend polling without DB query."""
    return NotificationListResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
    )


def get_notification_by_id(db: Session, notification_id: int) -> Optional[Any]:
    return None


def create_notification(db: Session, body: NotificationCreate) -> Any:
    raise ValueError("Notification table has been decommissioned")


def update_notification(
    db: Session, notification_id: int, body: NotificationUpdate
) -> Optional[Any]:
    return None


def delete_notification(db: Session, notification_id: int) -> bool:
    return True


def check_long_holding_stock(db: Session) -> List[Any]:
    return []


def resolve_notification(
    db: Session, notification_id: int
) -> Optional[Any]:
    return None


def check_and_create_notifications_under_over_min_max(
    db: Session, item: Any, type: str
) -> List[Any]:
    return []
