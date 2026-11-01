from app.core.celery_app import celery_app
from app.core.database import db_session
from app.core.logger import get_logger
from app.modules.robot.robot_service import task_status_service

logger = get_logger("main")


@celery_app.task(
    name="robot.persist_task_status",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def persist_task_status(self, payload: dict) -> int:
    order_id = payload.get("orderId")
    logger.info("Processing task status for order_id=%s", order_id)

    try:
        with db_session() as db:
            record = task_status_service.receive_task_status(db, payload)
            if record:
                return {"code": 1000, "order_id": order_id}
            else:
                return None

    except ValueError as exc:
        logger.error("Invalid task status payload (order_id=%s): %s", order_id, exc)
        raise

    except Exception as exc:
        logger.exception("Failed to persist task status (order_id=%s)", order_id)
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))