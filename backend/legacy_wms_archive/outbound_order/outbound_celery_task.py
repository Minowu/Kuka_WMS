from __future__ import annotations

from typing import Any, Optional

from fastapi.encoders import jsonable_encoder

from app.core.celery_app import celery_app
from app.core.database import db_session
from app.core.logger import get_logger
from app.modules.warehouse.outbound_order import outbound_order_service
from app.modules.warehouse.outbound_order.outbound_order_schema import (
    CalculateOutboundDetail,
    OutboundOrderCreate,
    OutboundOrderUpdate,
    OutboundRobotTaskCreate,
)

logger = get_logger("main")


def _dump(result: Any) -> Any:
    if result is None:
        return None
    return jsonable_encoder(result)


@celery_app.task(name="outbound.create_order", acks_late=True)
def create_outbound_order_task(body: dict, user_id: int) -> Any:
    logger.info("outbound.create_order order_code=%s", body.get("order_code"))
    with db_session() as db:
        result = outbound_order_service.create_outbound_order(
            db,
            OutboundOrderCreate.model_validate(body),
            user_id=user_id,
        )
        return _dump(result)


@celery_app.task(name="outbound.get_order_by_id", acks_late=True)
def get_outbound_order_by_id_task(order_id: int) -> Optional[Any]:
    logger.info("outbound.get_order_by_id order_id=%s", order_id)
    with db_session() as db:
        order = outbound_order_service.get_outbound_order_by_id(db, order_id)
        if order is None:
            return None
        return _dump(order)


@celery_app.task(name="outbound.get_robot_tasks", acks_late=True)
def get_outbound_robot_tasks_task(order_id: int) -> Any:
    logger.info("outbound.get_robot_tasks order_id=%s", order_id)
    with db_session() as db:
        tasks = outbound_order_service.get_outbound_robot_tasks(db, order_id)
        return _dump(tasks)


@celery_app.task(name="outbound.get_manual_allocation_tasks", acks_late=True)
def get_outbound_manual_allocation_tasks_task(order_id: int) -> Any:
    logger.info("outbound.get_manual_allocation_tasks order_id=%s", order_id)
    with db_session() as db:
        tasks = outbound_order_service.summarize_manual_allocation_tasks(
            db, order_id
        )
        return _dump(tasks)


@celery_app.task(name="outbound.get_order_details", acks_late=True)
def get_outbound_order_details_task(order_id: int) -> Optional[Any]:
    logger.info("outbound.get_order_details order_id=%s", order_id)
    with db_session() as db:
        details = outbound_order_service.get_outbound_order_detail(db, order_id)
        if details is None:
            return None
        return _dump(details)


@celery_app.task(name="outbound.get_lacked_details", acks_late=True)
def get_outbound_lacked_details_task(order_id: int) -> Any:
    logger.info("outbound.get_lacked_details order_id=%s", order_id)
    with db_session() as db:
        order = outbound_order_service.get_outbound_order_by_id(db, order_id)
        if order is None:
            return None
        lacked = outbound_order_service.lacked_details(db, order_id)
        return _dump(lacked)


@celery_app.task(name="outbound.calculate_order", acks_late=True)
def calculate_outbound_order_task(body: dict, strategy: str = "fefo") -> Any:
    logger.info(
        "outbound.calculate_order outbound_order_id=%s",
        body.get("outbound_order_id"),
    )
    with db_session() as db:
        result = outbound_order_service.calculate_outbound_order(
            db,
            CalculateOutboundDetail.model_validate(body),
            strategy=strategy,
        )
        return _dump(result)


@celery_app.task(name="outbound.execute_task", bind=True, max_retries=3, acks_late=True)
def execute_outbound_task_task(
    self,
    body: dict,
    detail_type: str = "auto",
) -> None:
    logger.info("outbound.execute_task order_id=%s", body.get("order_id"))
    try:
        with db_session() as db:
            outbound_order_service.execute_outbound_task(
                db,
                OutboundRobotTaskCreate.model_validate(body),
                detail_type=detail_type,
            )
    except Exception as exc:
        from app.modules.robot.robot_service import IcsError

        if isinstance(exc, IcsError) and exc.retryable and self.request.retries < self.max_retries:
            countdown = 10 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        raise


@celery_app.task(name="outbound.update_order", acks_late=True)
def update_outbound_order_task(
    order_id: int,
    body: dict,
    outbound_type: str,
    user_id: int,
) -> Any:
    logger.info("outbound.update_order order_id=%s", order_id)
    with db_session() as db:
        order = outbound_order_service.update_outbound_order(
            db,
            order_id,
            OutboundOrderUpdate.model_validate(body),
            outbound_type,
            user_id=user_id,
        )
        return _dump(order)
