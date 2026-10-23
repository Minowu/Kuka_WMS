"""KUKA Fleet Manager Webhook Callback Handler and Finite State Machine (FSM)."""

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient
from app.modules.production.production_models import (
    FLEET_MISSION_STATUS,
    MAPPING_STATUS,
    FleetTask,
    TaskStatus,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("main")


class WebhookHandler:
    """Handles incoming KUKA Fleet callbacks (/api/v1/receive-status) and FSM transitions."""

    def __init__(self, fleet_client: KukaFleetClient):
        self.fleet_client = fleet_client

    def receive_task_status(
        self,
        db: Session,
        payload: dict[str, Any],
        on_completed_fn: Optional[Callable[..., Any]] = None,
    ) -> Optional[TaskStatus]:
        """Process incoming callback webhook from KUKA Fleet Manager (/api/v1/receive-status)."""
        mission_code = (
            payload.get("missionCode")
            or payload.get("mission_code")
            or payload.get("orderId")
        )
        if not mission_code:
            logger.warning("Fleet webhook missing missionCode in payload: %s", payload)
            return None

        mission_code_str = str(mission_code).strip()
        raw_status = str(payload.get("missionStatus") or payload.get("mission_status") or payload.get("status") or "").strip()
        robot_id = str(payload.get("robotId") or payload.get("robot_id") or payload.get("deviceCode") or "").strip() or None
        container_code = str(payload.get("containerCode") or payload.get("container_code") or payload.get("shelfNumber") or "").strip() or None
        location_code = str(payload.get("containerLocationCode") or "").strip() or None
        curr_pos = str(payload.get("currentPosition") or "").strip() or None
        map_code = str(payload.get("mapCode") or "").strip() or None
        org_id = str(payload.get("orgId") or "").strip() or None
        msg = str(payload.get("message") or "").strip() or None

        robot_x = None
        robot_y = None
        try:
            rx_val = payload.get("robotX")
            if rx_val not in ("", None):
                robot_x = float(rx_val)
            ry_val = payload.get("robotY")
            if ry_val not in ("", None):
                robot_y = float(ry_val)
        except (ValueError, TypeError):
            pass

        # 1. Audit log in task_status
        record = TaskStatus(
            mission_code=mission_code_str,
            mission_status=raw_status,
            robot_id=robot_id,
            container_code=container_code,
            container_location_code=location_code,
            current_position=curr_pos,
            robot_x=robot_x,
            robot_y=robot_y,
            org_id=org_id,
            map_code=map_code,
            message=msg,
            raw_payload=payload,
        )
        db.add(record)
        db.flush()

        # 2. Lock FleetTask by mission_code
        fleet_task = (
            db.query(FleetTask)
            .filter(FleetTask.mission_code == mission_code_str)
            .with_for_update(of=FleetTask)
            .first()
        )
        if not fleet_task:
            logger.warning("Received status '%s' for unknown missionCode=%s", raw_status, mission_code_str)
            db.commit()
            db.refresh(record)
            return record

        # 3. Check for immutable final states
        if fleet_task.status in ("completed", "failed", "cancelled"):
            logger.info("FleetTask %s already in terminal state '%s', ignoring event '%s'", mission_code_str, fleet_task.status, raw_status)
            db.commit()
            db.refresh(record)
            return record

        fleet_task.last_mission_status = raw_status
        if curr_pos:
            fleet_task.current_position = curr_pos
        if robot_id:
            fleet_task.robot_id = robot_id

        # 4. State transition
        mapped_status = FLEET_MISSION_STATUS.get(raw_status) or MAPPING_STATUS.get(raw_status)

        if raw_status in ("MOVE_BEGIN", "ARRIVED"):
            fleet_task.status = "in_progress"
            if fleet_task.request:
                fleet_task.request.status = "in_progress"
            db.commit()

        elif raw_status == "UP_CONTAINER":
            fleet_task.status = "in_progress"
            fleet_task.picked_up_at = datetime.now(timezone.utc)
            if fleet_task.request:
                fleet_task.request.status = "in_progress"
            if fleet_task.container_id:
                cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
                if cart:
                    cart.is_locked = True
                    cart.locked_by_mission_code = mission_code_str
            db.commit()

        elif raw_status == "DOWN_CONTAINER":
            fleet_task.status = "in_progress"
            db.commit()

        elif raw_status == "COMPLETED" or mapped_status == "completed":
            db.commit()
            if on_completed_fn:
                on_completed_fn(db, mission_code_str)

        elif mapped_status in ("failed", "cancelled") or raw_status in ("FAILED", "CANCELLED", "CANCEL"):
            term_status = "cancelled" if "cancel" in raw_status.lower() else "failed"
            fleet_task.status = term_status
            fleet_task.error_message = msg or f"Fleet reported {raw_status}"
            if fleet_task.request:
                fleet_task.request.status = term_status
            if fleet_task.container_id:
                cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
                if cart:
                    cart.is_locked = False
                    cart.locked_by_mission_code = None
                    cart.destination_location_id = None
            db.commit()
        else:
            db.commit()

        db.refresh(record)
        return record

    def complete_fleet_task(
        self,
        db: Session,
        mission_code: str,
        on_after_complete_fn: Optional[Callable[..., Any]] = None,
    ) -> FleetTask:
        """Official completion handler when KUKA Fleet reports COMPLETED."""
        fleet_task = (
            db.query(FleetTask)
            .filter(FleetTask.mission_code == mission_code)
            .with_for_update(of=FleetTask)
            .first()
        )
        if not fleet_task:
            raise ValueError(f"Không tìm thấy FleetTask '{mission_code}'.")

        now = datetime.now(timezone.utc)
        fleet_task.status = "completed"
        fleet_task.completed_at = now

        req_type = None
        if fleet_task.request:
            req_type = fleet_task.request.request_type
            fleet_task.request.status = "completed"
            fleet_task.request.completed_at = now

        dropoff_loc = (
            db.query(Location).filter(Location.id == fleet_task.dropoff_location_id).first()
            if fleet_task.dropoff_location_id
            else None
        )
        is_empty_buffer_dropoff = bool(
            req_type == "RETURN_EMPTY_CART"
            or (dropoff_loc and dropoff_loc.location_type == "EMPTY_CART_BUFFER")
        )

        if fleet_task.container_id:
            cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
            if cart:
                if is_empty_buffer_dropoff:
                    if dropoff_loc and cart.container_code:
                        try:
                            self.fleet_client.fleet_container_out(
                                location_code=dropoff_loc.location_code,
                                container_code=cart.container_code,
                                db=db,
                            )
                        except Exception as e:
                            logger.error("Could not call fleet_container_out: %s", e)
                    cart.location_id = None
                    cart.destination_location_id = None
                    cart.quantity = 0
                    cart.current_stage_level = 0
                    cart.status = "empty"
                    cart.is_active = False
                    cart.is_locked = False
                    cart.locked_by_mission_code = None
                else:
                    cart.location_id = fleet_task.dropoff_location_id
                    cart.destination_location_id = None
                    cart.is_locked = False
                    cart.locked_by_mission_code = None
                    cart.status = "available"

        db.commit()

        if on_after_complete_fn:
            on_after_complete_fn(db)

        return fleet_task
