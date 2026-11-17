"""KUKA Fleet Manager Webhook Callback Handler and Finite State Machine (FSM)."""

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger, bind_context
from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient, fail_and_release
from app.modules.production.production_models import (
    FLEET_MISSION_STATUS,
    MAPPING_STATUS,
    FleetTask,
    TaskStatus,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.fleet.webhook")


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
        except (ValueError, TypeError) as exc:
            logger.warning(
                "Failed parsing robot coordinates (robotX=%s, robotY=%s): %s",
                payload.get("robotX"),
                payload.get("robotY"),
                exc,
                exc_info=True,
            )

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
        # Lưu cứng tín hiệu webhook vào DB ngay lập tức để không bao giờ bị rollback mất log audit
        db.commit()
        db.refresh(record)

        # 2. Lock FleetTask by mission_code
        fleet_task = (
            db.query(FleetTask)
            .filter(FleetTask.mission_code == mission_code_str)
            .with_for_update(of=FleetTask)
            .first()
        )
        if not fleet_task:
            logger.warning(
                "Received status '%s' for unknown missionCode=%s",
                raw_status,
                mission_code_str,
                extra={"mission_code": mission_code_str, "raw_status": raw_status, "reason": "unknown_mission_code"},
            )
            db.commit()
            db.refresh(record)
            return record

        bind_context(fleet_task_id=fleet_task.id)

        # 3. Check for immutable final states
        if fleet_task.status in ("completed", "failed", "cancelled"):
            logger.warning(
                "Duplicate/terminal webhook event ignored for FleetTask %s (mission_code=%s): already in terminal state '%s', received event '%s'",
                fleet_task.id,
                mission_code_str,
                fleet_task.status,
                raw_status,
                extra={
                    "fleet_task_id": fleet_task.id,
                    "mission_code": mission_code_str,
                    "status": fleet_task.status,
                    "raw_status": raw_status,
                    "reason": "terminal_state",
                },
            )
            db.commit()
            db.refresh(record)
            return record

        if fleet_task.last_mission_status == raw_status:
            logger.debug(
                "Duplicate webhook status event '%s' received for FleetTask %s (mission_code=%s)",
                raw_status,
                fleet_task.id,
                mission_code_str,
                extra={
                    "fleet_task_id": fleet_task.id,
                    "mission_code": mission_code_str,
                    "raw_status": raw_status,
                    "reason": "duplicate_event",
                },
            )

        now = datetime.now(timezone.utc)
        fleet_task.last_mission_status = raw_status
        fleet_task.updated_at = now
        if curr_pos:
            fleet_task.current_position = curr_pos
        if robot_id:
            fleet_task.robot_id = robot_id

        loc_ids = sorted(
            {
                int(lid)
                for lid in (fleet_task.pickup_location_id, fleet_task.dropoff_location_id)
                if lid is not None
            }
        )
        created_by = fleet_task.request.created_by if fleet_task.request else None
        recipient_user_ids = resolve_location_recipient_user_ids(
            db,
            loc_ids,
            extra_user_ids=[created_by],
        )

        # 4. State transition
        mapped_status = FLEET_MISSION_STATUS.get(raw_status) or MAPPING_STATUS.get(raw_status)
        old_status = fleet_task.status

        if not mapped_status and raw_status not in ("MOVE_BEGIN", "ARRIVED", "UP_CONTAINER", "DOWN_CONTAINER", "COMPLETED"):
            logger.warning(
                "Unmapped webhook status event '%s' received for FleetTask %s (mission_code=%s): no mapping in FLEET_MISSION_STATUS",
                raw_status,
                fleet_task.id,
                mission_code_str,
                extra={
                    "fleet_task_id": fleet_task.id,
                    "mission_code": mission_code_str,
                    "raw_status": raw_status,
                    "reason": "unmapped_status",
                },
            )

        if raw_status in ("MOVE_BEGIN", "ARRIVED"):
            fleet_task.status = "in_progress"
            if old_status != "in_progress":
                logger.info(
                    "FleetTask %s status mapping transition: %s -> in_progress (KUKA status: %s, mapped: %s)",
                    mission_code_str,
                    old_status,
                    raw_status,
                    mapped_status,
                    extra={
                        "fleet_task_id": fleet_task.id,
                        "mission_code": mission_code_str,
                        "old_status": old_status,
                        "new_status": "in_progress",
                        "raw_status": raw_status,
                        "mapped_status": mapped_status,
                    },
                )
            if fleet_task.request:
                fleet_task.request.status = "in_progress"
            db.commit()
            publish_event(
                "floor.changed",
                {
                    "reason": f"webhook_{raw_status.lower()}",
                    "mission_code": mission_code_str,
                    "location_ids": loc_ids,
                },
                user_ids=recipient_user_ids,
                admins=True,
            )

        elif raw_status == "UP_CONTAINER":
            fleet_task.status = "in_progress"
            fleet_task.picked_up_at = now
            if old_status != "in_progress":
                logger.info(
                    "FleetTask %s status mapping transition: %s -> in_progress (KUKA status: %s, mapped: %s)",
                    mission_code_str,
                    old_status,
                    raw_status,
                    mapped_status,
                    extra={
                        "fleet_task_id": fleet_task.id,
                        "mission_code": mission_code_str,
                        "old_status": old_status,
                        "new_status": "in_progress",
                        "raw_status": raw_status,
                        "mapped_status": mapped_status,
                    },
                )
            if fleet_task.request:
                fleet_task.request.status = "in_progress"
            if fleet_task.container_id:
                cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
                if cart:
                    cart.is_locked = True
                    cart.locked_by_mission_code = mission_code_str
                    # Giải phóng vị trí nguồn (Source Location) ngay khi AMR nhấc xe phôi lên:
                    # Xe phôi rời mặt sàn, đang nằm trên lưng AMR di chuyển tới đích.
                    cart.location_id = None
            db.commit()
            publish_event(
                "floor.changed",
                {
                    "reason": "webhook_up_container",
                    "mission_code": mission_code_str,
                    "location_ids": loc_ids,
                },
                user_ids=recipient_user_ids,
                admins=True,
            )

        elif raw_status == "DOWN_CONTAINER":
            fleet_task.status = "in_progress"
            if old_status != "in_progress":
                logger.info(
                    "FleetTask %s status mapping transition: %s -> in_progress (KUKA status: %s, mapped: %s)",
                    mission_code_str,
                    old_status,
                    raw_status,
                    mapped_status,
                    extra={
                        "fleet_task_id": fleet_task.id,
                        "mission_code": mission_code_str,
                        "old_status": old_status,
                        "new_status": "in_progress",
                        "raw_status": raw_status,
                        "mapped_status": mapped_status,
                    },
                )
            if fleet_task.container_id and fleet_task.dropoff_location_id:
                cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.container_id).first()
                if cart:
                    # Xe phôi chạm sàn tại vị trí đích
                    cart.location_id = fleet_task.dropoff_location_id
            db.commit()
            publish_event(
                "floor.changed",
                {
                    "reason": "webhook_down_container",
                    "mission_code": mission_code_str,
                    "location_ids": loc_ids,
                },
                user_ids=recipient_user_ids,
                admins=True,
            )

        elif raw_status == "COMPLETED" or mapped_status == "completed":
            logger.info(
                "FleetTask %s status mapping transition: %s -> completed (KUKA status: %s, mapped: %s)",
                mission_code_str,
                old_status,
                raw_status,
                mapped_status,
                extra={
                    "fleet_task_id": fleet_task.id,
                    "mission_code": mission_code_str,
                    "old_status": old_status,
                    "new_status": "completed",
                    "raw_status": raw_status,
                    "mapped_status": mapped_status,
                },
            )
            db.commit()
            if on_completed_fn:
                on_completed_fn(db, mission_code_str)

        elif mapped_status in ("failed", "cancelled") or raw_status in (
            "FAILED",
            "CANCELED",
            "CANCELLED",
            "CANCEL",
            "ABORTED",
            "ABORT",
            "EXCEPTION",
            "TERMINATED",
            "TIMEOUT",
            "ERROR",
        ):
            term_status = "cancelled" if "cancel" in raw_status.lower() else "failed"
            err_msg = msg or f"Fleet reported {raw_status}"
            logger.info(
                "FleetTask %s status mapping transition: %s -> %s (KUKA status: %s, mapped: %s)",
                mission_code_str,
                old_status,
                term_status,
                raw_status,
                mapped_status,
                extra={
                    "fleet_task_id": fleet_task.id,
                    "mission_code": mission_code_str,
                    "old_status": old_status,
                    "new_status": term_status,
                    "raw_status": raw_status,
                    "mapped_status": mapped_status,
                },
            )
            # Dùng fail_and_release để mở khóa xe, khôi phục nghiệp vụ và tự động xếp hàng phát
            # sự kiện WebSocket `fleet.task_failed` + `floor.changed` ngay sau khi db.commit()!
            fail_and_release(
                db,
                fleet_task,
                err_msg,
                is_cancelled=(term_status == "cancelled"),
            )
            db.commit()
        else:
            logger.warning(
                "Unmapped or unhandled webhook event '%s' for FleetTask %s (mission_code=%s): no FSM transition executed",
                raw_status,
                fleet_task.id,
                mission_code_str,
                extra={
                    "fleet_task_id": fleet_task.id,
                    "mission_code": mission_code_str,
                    "raw_status": raw_status,
                    "reason": "unmapped_or_unhandled",
                },
            )
            db.commit()

        db.refresh(record)
        return record


    def complete_fleet_task(
        self,
        db: Session,
        mission_code: str,
        on_after_complete_fn: Optional[Callable[..., Any]] = None,
    ) -> FleetTask:
        from app.modules.production.dispatch.webhook_complete import (
            complete_fleet_task as _complete,
        )

        return _complete(
            self.fleet_client,
            db,
            mission_code,
            on_after_complete_fn=on_after_complete_fn,
        )
