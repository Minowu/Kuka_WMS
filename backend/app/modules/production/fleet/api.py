"""REST API: KUKA Fleet Manager webhook callback (thin router)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.application.fleet.use_cases.handle_webhook import HandleWebhookRequest
from app.core.database import get_db
from app.core.logger import get_logger
from app.infrastructure.di.production_factory import get_handle_webhook_use_case

fleet_router = APIRouter(tags=["Production - Fleet Webhook"])
webhook_log = get_logger("wms.fleet.webhook")

DbSession = Annotated[Session, Depends(get_db)]


@fleet_router.post(
    "/production/fleet/receive-status",
    status_code=status.HTTP_200_OK,
)
def receive_task_status(payload: dict[str, Any], db: DbSession) -> dict[str, Any]:
    """
    Webhook tiếp nhận trạng thái từ KUKA Fleet Manager.
    Luôn trả về HTTP 200 theo quy định của KUKA Fleet.
    """
    try:
        webhook_log.info("Fleet webhook received", extra={"payload": payload})
    except Exception:
        pass
    try:
        result = get_handle_webhook_use_case(db).execute(HandleWebhookRequest(payload=payload))
        return {"code": result.code, "message": result.message}
    except Exception as e:
        db.rollback()
        webhook_log.exception(
            "Error processing KUKA Fleet webhook (transaction rolled back): %s", e
        )
        return {"code": 0, "message": "success"}
