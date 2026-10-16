import httpx
from sqlalchemy.orm import Session
import json

from app.core.config import settings
from app.modules.warehouse.lot_number_utils import format_lot_number_display
from app.modules.robot.robot_model import RobotTask, TaskStatus, MAPPING_STATUS
from app.modules.warehouse.inbound_order.inbound_order_model import InboundOrderDetail
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.inbound_order.inbound_order_schema import InboundOrderDetailResponse
from app.modules.warehouse.outbound_order.outbound_order_model import OutboundOrderAllocation
from app.modules.warehouse.transaction_history.history_model import Transaction, History
from app.modules.warehouse.notificcation.notification_service import check_and_create_notifications_under_over_min_max
from app.core.logger import get_logger
from app.core.cache import cache_set
logger = get_logger("main")

ICS_ADD_TASK_PATH = f"{settings.ics_base_url.rstrip('/')}:7000/ics/taskOrder/addTask"

class IcsError(Exception):
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable

class TaskStatusService:
    def __init__(self):
        self.current = None

    def add_task(self, payload: dict) -> dict:
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0)) as client:
                response = client.post(ICS_ADD_TASK_PATH, json=payload)
                response.raise_for_status()
                data = response.json()
            logger.info(f"ICS addTask response: {data}")
            return data
        except httpx.HTTPStatusError as e:
            retryable = e.response.status_code >= 500
            raise IcsError("ICS server error", retryable=retryable) from e
        except httpx.RequestError as e:
            raise IcsError("Cannot reach ICS server", retryable=True) from e

    def create_robot_task(self, db: Session, task: RobotTask, not_inserted: bool = True) -> RobotTask:
        payload = {
            "orderId": task.order_id,
            "modelProcessCode": task.process_code,
            "fromSystem": task.system_code,
            "taskOrderDetail": json.loads(task.task_order_detail),
        }
        try:
            self.add_task(payload)
            if not_inserted:
                db.add(task)
                db.commit()
                db.refresh(task)
            return task
        except Exception:
            db.rollback()
            raise

    def _settle_inbound_stock(self, db: Session, detail: InboundOrderDetail) -> None:
        if not detail.to_location_id:
            return

        stocks = (
            db.query(ItemStock)
            .filter(
                ItemStock.inbound_order_detail_id == detail.id,
                ItemStock.is_active.is_(True),
                ItemStock.status != "virtual",
            )
            .all()
        )

        check_and_create_notifications_under_over_min_max(db, stocks[0].item, "under")

        for stock in stocks:
            logger.info(f"Current status: {stock.status}")
            stock.location_id = detail.to_location_id
            if stock.status != "split":
                stock.status = "available"
            logger.info(f"New status: {stock.status}")

            db.add(Transaction(
                    from_location_id=detail.from_location_id,
                    to_location_id=detail.to_location_id,
                    transaction_type="inbound",
                    item_stock_id=stock.id,
                    quantity=int(stock.quantity),
                    created_by_id=detail.inbound_order.created_by_id,
                ))

        db.add(History(
            inbound_order_id=detail.inbound_order_id,
            old_status="in_progress",
            new_status="completed",
            description=f"Inbound order detail {detail.id} completed",
            details=InboundOrderDetailResponse.model_validate(detail).model_dump(mode="json"),
            created_by_id=detail.inbound_order.created_by_id,
        ))
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    def receive_task_status(self, db: Session, payload: dict) -> TaskStatus:
        order_id = payload.get("orderId")
        if not order_id:
            raise ValueError("orderId is required")

        robot_task = db.query(RobotTask).filter(RobotTask.order_id == order_id).first()
        if not robot_task:
            raise ValueError("Robot task not found")

        if robot_task.status == "completed":
            return

        if robot_task.inbound_order_detail_id is not None:
            detail = robot_task.inbound_order_detail
        elif robot_task.outbound_order_allocations is not None:
            allocations = robot_task.outbound_order_allocations
            
        else:
            raise ValueError("Order not found")

        ics_status = str(payload.get("status"))
        if ics_status in MAPPING_STATUS:
            if robot_task.inbound_order_detail_id is not None:
                detail.status = MAPPING_STATUS[ics_status]
                if MAPPING_STATUS[ics_status] == "completed":
                    logger.info(f"Receive completed for {order_id}")
                    self._settle_inbound_stock(db, detail)
            else:
                for allocation in allocations:
                    allocation.status = (
                        "pre_completed"
                        if MAPPING_STATUS[ics_status] == "completed" and allocation.allocation_type == "outbound"
                        else MAPPING_STATUS[ics_status]
                    )

                    if allocation.status == "completed":
                        from app.modules.warehouse.outbound_order.outbound_order_service import (
                            _settle_outbound_stock,
                        )
                        _settle_outbound_stock(db, [allocation])

                if MAPPING_STATUS[ics_status] == "completed":
                    from_location = allocations[0].from_location
                    to_location = allocations[0].to_location
                    if not from_location or not to_location:
                        raise ValueError("From location or to location not found")
                    stocks = db.query(ItemStock).filter(ItemStock.location_id == from_location.id, ItemStock.is_active.is_(True)).all()
                    for stock in stocks:
                        stock.location_id = to_location.id

                
        record = TaskStatus(
            sub_task_status=payload.get("subTaskStatus"),
            order_id=str(order_id),
            device_code=payload.get("deviceCode"),
            device_num=payload.get("deviceNum"),
            qr_code=payload.get("qrCode"),
            shelf_number=payload.get("shelfNumber"),
            status=str(payload.get("status")),
        )
        try:
            db.add(record)
            db.commit()
            db.refresh(record)
            return record
        except Exception:
            db.rollback()
            raise

    
task_status_service = TaskStatusService()