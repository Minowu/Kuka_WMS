"""Robot / ICS webhook API."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.core.celery_app import run_logic_task
from app.modules.robot.robot_celery_task import persist_task_status
from app.core.logger import get_logger

logger = get_logger("main")
router = APIRouter(tags=["Robot"])


@router.post("/receive-status", status_code=status.HTTP_200_OK)
def receive_task_status(payload: dict[str, Any]) -> dict[str, int]:
    if not payload.get("orderId"):
        return {"code": 1000}
    try:
        result = run_logic_task(persist_task_status, payload=payload)
        if result:
            return {"code": 1000}
        else:
            logger.info(f"Status fail for order_id={payload.get('orderId')}")
            return {"code": 1000}
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
