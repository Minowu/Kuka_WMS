"""Celery background tasks for KUKA Fleet Manager (/receive-status) callbacks and Always-Scan TransportQueue."""

from typing import Any, Optional

from app.core.celery_app import celery_app
from app.core.database import db_session
from app.core.logger import get_logger
from app.modules.production.dispatch_service import dispatch_service

logger = get_logger("main")


@celery_app.task(
    name="robot.persist_task_status",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def persist_task_status(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    order_id = payload.get("orderId")
    logger.info("Processing fleet task status for order_id=%s", order_id)

    try:
        with db_session() as db:
            record = dispatch_service.receive_task_status(db, payload)
            if record:
                return {"code": 1000, "order_id": str(order_id)}
            return None

    except ValueError as exc:
        logger.error("Invalid fleet task status payload (order_id=%s): %s", order_id, exc)
        raise

    except Exception as exc:
        logger.exception("Failed to persist fleet task status (order_id=%s)", order_id)
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))


@celery_app.task(
    name="production.scan_transport_queue",
    acks_late=True,
)
def scan_transport_queue() -> dict[str, int]:
    """
    Periodic 'Always Scan' worker that checks `TransportQueue` (`WAITING_CART` & `WAITING_SLOT`)
    and automatically dispatches AMRs whenever matching carts or slots become available.
    """
    with db_session() as db:
        result = dispatch_service.scan_all_transport_queues(db)
        if result["resolved_waiting_cart"] or result["resolved_waiting_slot"]:
            logger.info("Always-Scan resolved transport queues: %s", result)
        return result
