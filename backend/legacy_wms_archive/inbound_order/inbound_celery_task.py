from __future__ import annotations

from typing import Any, Optional

from fastapi.encoders import jsonable_encoder

from app.core.celery_app import celery_app
from app.core.database import db_session
from app.core.logger import get_logger
from app.modules.warehouse.inbound_order import inbound_order_service
from app.modules.warehouse.inbound_order.inbound_order_schema import (
    InboundOrderCreate,
    InboundOrderUpdate,
)

logger = get_logger("main")


def _dump(result: Any) -> Any:
    if result is None:
        return None
    if hasattr(result, "model_dump"):
        return jsonable_encoder(result.model_dump(mode="json"))
    return jsonable_encoder(result)


@celery_app.task(name="inbound.create_order", acks_late=True)
def create_inbound_order_task(
    body: dict,
    user_id: int,
    inbound_type: str,
) -> Any:
    logger.info("inbound.create_order order_code=%s", body.get("order_code"))
    with db_session() as db:
        order = inbound_order_service.create_inbound_order(
            db,
            InboundOrderCreate.model_validate(body),
            user_id=user_id,
            inbound_type=inbound_type,
        )
        return _dump(order)


@celery_app.task(name="inbound.update_order", acks_late=True)
def update_inbound_order_task(
    order_code: str,
    body: dict,
    inbound_type: str,
    user_id: int,
) -> Any:
    logger.info("inbound.update_order order_code=%s", order_code)
    with db_session() as db:
        order = inbound_order_service.update_inbound_order(
            db,
            order_code,
            InboundOrderUpdate.model_validate(body),
            inbound_type,
            user_id=user_id,
        )
        return _dump(order)


@celery_app.task(name="inbound.get_order_details", acks_late=True)
def get_inbound_order_details_task(order_code: str) -> Optional[Any]:
    logger.info("inbound.get_order_details order_code=%s", order_code)
    with db_session() as db:
        details = inbound_order_service.get_inbound_order_detail(db, order_code)
        if details is None:
            return None
        return _dump(details)


@celery_app.task(name="inbound.accept_task", bind=True, max_retries=3, acks_late=True)
def accept_inbound_task_task(self, detail_id: int) -> Any:
    logger.info("inbound.accept_task detail_id=%s", detail_id)
    try:
        with db_session() as db:
            result = inbound_order_service.execute_inbound_task(db, detail_id)
            return _dump(result)
    except Exception as exc:
        from app.modules.robot.robot_service import IcsError

        if isinstance(exc, IcsError) and exc.retryable and self.request.retries < self.max_retries:
            countdown = 10 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        raise


@celery_app.task(name="inbound.caller_order", acks_late=True)
def caller_inbound_order_task(
    body: dict,
    user_id: int,
    inbound_type: str,
) -> Any:
    logger.info("inbound.caller_order order_code=%s", body.get("order_code"))
    with db_session() as db:
        order = inbound_order_service.caller_inbound_order(
            db,
            InboundOrderCreate.model_validate(body),
            user_id=user_id,
            inbound_type=inbound_type,
        )
        return _dump(order)
