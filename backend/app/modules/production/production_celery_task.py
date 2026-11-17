"""Các tác vụ chạy ngầm Celery cho việc gửi lệnh KUKA Fleet, bộ quét phục hồi lỗi (Sweeper) và quét hàng đợi tự động (Always-Scan)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.celery_app import celery_app
from app.core.database import db_session
from app.core.logger import get_logger
from app.modules.production.dispatch.kuka_fleet_client import fail_and_release
from app.modules.production.dispatch.service import dispatch_service
from app.modules.production.production_models import FleetTask

logger = get_logger("main")

MAX_FLEET_SUBMIT_ATTEMPTS = 5


def enqueue_fleet_submit(fleet_task_id: int) -> None:
    """
    Đẩy tác vụ `production.submit_fleet_task` vào hàng đợi Redis `fleet` một cách an toàn SAU KHI đã `db.commit()`.
    Bọc `try/except` để không bao giờ làm văng lỗi API nếu Redis mất kết nối tạm thời — tác vụ định kỳ
    `sweep_fleet_tasks` sẽ tự động quét và đẩy lại sau đó.
    """
    try:
        submit_fleet_task.delay(fleet_task_id)
    except Exception as exc:
        logger.error(
            "Failed to enqueue submit_fleet_task for fleet_task_id=%s (sweeper will recover): %s",
            fleet_task_id,
            exc,
        )


@celery_app.task(
    name="production.submit_fleet_task",
    bind=True,
    max_retries=MAX_FLEET_SUBMIT_ATTEMPTS,
    default_retry_delay=5,
    acks_late=True,
    ignore_result=True,
    soft_time_limit=25,
    time_limit=30,
)
def submit_fleet_task(self, fleet_task_id: int) -> Optional[dict[str, Any]]:
    """Celery entry → SubmitTaskUseCase (Level C)."""
    from app.application.fleet.use_cases.submit_task import SubmitTaskRequest
    from app.infrastructure.di.fleet_factory import get_submit_task_use_case

    response = get_submit_task_use_case().execute(
        SubmitTaskRequest(fleet_task_id=fleet_task_id)
    )
    result = response.result or {
        "status": response.status,
        "fleet_task_id": fleet_task_id,
        "mission_code": response.mission_code,
    }
    if result.get("_should_retry") and getattr(self, "request", None) is not None and not getattr(
        self.request, "called_directly", True
    ):
        raise self.retry(
            exc=result.get("_retry_exc"),
            countdown=int(result.get("_retry_countdown") or 5),
        )
    # strip internal keys
    return {k: v for k, v in result.items() if not str(k).startswith("_")}

@celery_app.task(
    name="production.sweep_fleet_tasks",
    acks_late=True,
    ignore_result=True,
)
def sweep_fleet_tasks() -> dict[str, int]:
    """
    Bộ quét lưới an toàn (Sweeper) chạy định kỳ mỗi 15 giây (Bước S3 / Mục 1.4):
    1. Các task bị kẹt ở trạng thái `submitting` quá 60 giây (do worker bị sập giữa lúc gọi HTTP) -> trả về `pending_submit`.
    2. Các task `pending_submit` đã thử quá số lần tối đa (`submit_attempts >= MAX`) -> gọi `fail_and_release` mở khóa xe.
    3. Các task `pending_submit` cũ hơn 15 giây mà chưa vượt quá số lần thử -> đẩy lại vào hàng đợi `submit_fleet_task`.
    """
    now = datetime.now(timezone.utc)
    submitting_cutoff = now - timedelta(seconds=60)
    pending_cutoff = now - timedelta(seconds=15)

    reset_submitting = 0
    failed_exhausted = 0
    reenqueued = 0
    reenqueue_ids: list[int] = []

    with db_session() as db:
        # 1. Khôi phục các task bị kẹt ở trạng thái 'submitting' quá 60 giây
        stuck_submitting = (
            db.query(FleetTask)
            .filter(
                FleetTask.status == "submitting",
                FleetTask.updated_at < submitting_cutoff,
            )
            .with_for_update(of=FleetTask, skip_locked=True)
            .all()
        )
        for t in stuck_submitting:
            logger.warning(
                "Sweeper resetting stuck 'submitting' FleetTask %s (attempts=%s) back to 'pending_submit'",
                t.mission_code,
                t.submit_attempts,
            )
            t.status = "pending_submit"
            t.updated_at = now
            reset_submitting += 1
        if reset_submitting:
            db.commit()

        # 2 & 3. Xử lý các task 'pending_submit' bị đọng quá 15 giây
        stale_pending = (
            db.query(FleetTask)
            .filter(
                FleetTask.status == "pending_submit",
                FleetTask.updated_at < pending_cutoff,
            )
            .with_for_update(of=FleetTask, skip_locked=True)
            .all()
        )
        for t in stale_pending:
            if (t.submit_attempts or 0) >= MAX_FLEET_SUBMIT_ATTEMPTS:
                reason = t.error_message or f"Quá số lần thử gửi lệnh tới KUKA Fleet ({t.submit_attempts} lần)."
                logger.error(
                    "Sweeper failing exhausted FleetTask %s (attempts=%s): %s",
                    t.mission_code,
                    t.submit_attempts,
                    reason,
                )
                fail_and_release(db, t, reason)
                failed_exhausted += 1
            else:
                logger.info(
                    "Sweeper re-enqueueing pending FleetTask %s (id=%s, attempts=%s)",
                    t.mission_code,
                    t.id,
                    t.submit_attempts,
                )
                t.updated_at = now
                reenqueue_ids.append(t.id)
                reenqueued += 1

        if failed_exhausted or reenqueued:
            db.commit()

        if failed_exhausted:
            try:
                dispatch_service.scan_all_transport_queues(db)
            except Exception as exc:
                logger.warning("Queue scan after sweeper fail_and_release warning: %s", exc)

    for tid in reenqueue_ids:
        enqueue_fleet_submit(tid)

    return {
        "reset_submitting": reset_submitting,
        "failed_exhausted": failed_exhausted,
        "reenqueued": reenqueued,
    }


@celery_app.task(
    name="robot.persist_task_status",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
    ignore_result=True,
)
def persist_task_status(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Celery entry → HandleWebhookUseCase (Level C)."""
    mission_code = payload.get("missionCode") or payload.get("mission_code") or payload.get("orderId")
    logger.info("Processing fleet task status for mission_code=%s", mission_code)

    try:
        from app.application.fleet.use_cases.handle_webhook import HandleWebhookRequest
        from app.infrastructure.di.production_factory import get_handle_webhook_use_case

        with db_session() as db:
            resp = get_handle_webhook_use_case(db).execute(HandleWebhookRequest(payload=payload))
            if resp.task_status:
                return {"code": 0, "mission_code": str(mission_code)}
            return None

    except ValueError as exc:
        logger.error("Invalid fleet task status payload (mission_code=%s): %s", mission_code, exc)
        raise

    except Exception as exc:
        logger.exception("Failed to persist fleet task status (mission_code=%s)", mission_code)
        raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))


@celery_app.task(
    name="production.scan_transport_queue",
    acks_late=True,
    ignore_result=True,
)
def scan_transport_queue() -> dict[str, int]:
    """
    Worker định kỳ 'Always Scan' → application scan use case (Level C).
    """
    from app.application.production.use_cases.queue_scan.scan_transport_queues import (
        ScanTransportQueuesUseCase,
    )

    with db_session() as db:
        result = ScanTransportQueuesUseCase(dispatch_service).execute(db)
        if result["resolved_waiting_cart"] or result["resolved_waiting_slot"]:
            logger.info("Always-Scan resolved transport queues: %s", result)
        return result
