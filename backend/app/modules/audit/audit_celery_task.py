"""Nightly retention cleanup for audit/action logs."""
from app.core.celery_app import celery_app
from app.core.database import db_session
from app.core.logger import get_logger
from app.modules.audit.audit_service import cleanup_expired_logs

logger = get_logger("wms.audit")


@celery_app.task(name="audit.cleanup_expired_logs")
def cleanup_expired_logs_task() -> dict[str, int]:
    with db_session() as db:
        deleted = cleanup_expired_logs(db)
    logger.info("Audit retention cleanup done: %s", deleted, extra=deleted)
    return deleted
