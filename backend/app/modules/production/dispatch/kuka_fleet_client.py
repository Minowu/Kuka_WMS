"""KUKA Fleet Manager (ICS/RCS) HTTP Adapter & Command Hooks."""

from app.modules.warehouse.location_map.location_model import Location
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.modules.production.production_models import FleetApiCall, FleetTask

logger = get_logger("main")


def _ics_configured() -> bool:
    base = (settings.kuka_base_url or "").strip()
    return bool(base and base != "Your RCS Server path" and base.startswith("http"))


class IcsError(Exception):
    """Exception raised when communicating with KUKA Fleet Manager (ICS/RCS)."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class KukaFleetClient:
    """Handles all outbound HTTP POST communication with KUKA Fleet Manager."""

    def _post_kuka(
        self,
        endpoint_path: str,
        payload: dict[str, Any],
        api_name: str,
        mission_code: Optional[str] = None,
        container_code: Optional[str] = None,
        request_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """Low-level HTTP POST to KUKA Fleet Manager with audit logging in fleet_api_call."""
        req_id = request_id or str(payload.get("requestId") or f"REQ_{uuid.uuid4().hex[:12].upper()}")
        base = getattr(settings, "kuka_base_url", None) or getattr(settings, "kuka_base_url", "")
        base = base.rstrip("/")
        endpoint = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        url = f"{base}{endpoint}"

        if not _ics_configured():
            error_msg = f"KUKA Fleet API chưa được cấu hình hoặc offline — không thể điều xe {api_name}"
            logger.error(error_msg)
            err_resp = {"code": -1, "message": error_msg, "success": False}
            if db:
                call_log = FleetApiCall(
                    api_name=api_name,
                    request_id=req_id,
                    mission_code=mission_code,
                    container_code=container_code,
                    request_body=payload,
                    http_status=503,
                    response_body=err_resp,
                    error=error_msg,
                    success=False,
                )
                db.add(call_log)
                db.flush()
            raise IcsError(error_msg, retryable=False)

        timeout_sec = float(getattr(settings, "kuka_http_timeout_seconds", 5.0))
        http_status = None
        error_msg = None
        headers = {
            "Content-Type": "application/json",
            "orgId": getattr(settings, "kuka_org_id", "KUKA011021"),
        }
        token = getattr(settings, "kuka_access_token", None) or getattr(settings, "kuka_api_token", None)
        if token:
            headers["Authorization"] = token

        try:
            with httpx.Client(timeout=httpx.Timeout(timeout_sec)) as client:
                response = client.post(url, json=payload, headers=headers)
                http_status = response.status_code
                response.raise_for_status()
                resp_data = response.json()
            logger.info("KUKA Fleet POST %s [%s] response: %s", endpoint_path, api_name, resp_data)

            # Kiểm tra quy chuẩn phản hồi của KUKA Fleet Manager (code: 0/200 và success: True)
            fleet_success = resp_data.get("success") is True and str(resp_data.get("code", "")) in ("0", "200")
            fleet_code = str(resp_data.get("code", ""))
            fleet_msg = resp_data.get("message")

            # Lưu ý về mã 100502 từ KUKA RCS: "Container[xxx] doesn't exist".
            # Nếu Fleet thông báo xe chưa tồn tại trong danh mục RCS -> Fleet từ chối (fleet_success = False).
            # Tuyệt đối không ghi đè fleet_success = True khi RCS báo container doesn't exist!

            if db:
                call_log = FleetApiCall(
                    api_name=api_name,
                    request_id=req_id,
                    mission_code=mission_code,
                    container_code=container_code,
                    request_body=payload,
                    http_status=http_status,
                    response_body=resp_data,
                    success=fleet_success,
                    error=fleet_msg if not fleet_success else None,
                )
                db.add(call_log)
                db.flush()

            if not fleet_success:
                err_text = f"KUKA Fleet từ chối [{api_name}] (code={fleet_code}): {fleet_msg}"
                logger.warning(err_text)
                raise IcsError(err_text, retryable=False)

            return resp_data
        except httpx.HTTPStatusError as e:
            http_status = e.response.status_code
            error_msg = f"KUKA Fleet server error ({http_status}): {e.response.text}"
            if db:
                call_log = FleetApiCall(
                    api_name=api_name,
                    request_id=req_id,
                    mission_code=mission_code,
                    container_code=container_code,
                    request_body=payload,
                    http_status=http_status,
                    response_body=None,
                    success=False,
                    error=error_msg,
                )
                db.add(call_log)
                db.flush()
            raise IcsError(error_msg, retryable=(http_status >= 500)) from e
        except httpx.RequestError as e:
            error_msg = f"Cannot reach KUKA Fleet server: {e}"
            if db:
                call_log = FleetApiCall(
                    api_name=api_name,
                    request_id=req_id,
                    mission_code=mission_code,
                    container_code=container_code,
                    request_body=payload,
                    http_status=None,
                    response_body=None,
                    success=False,
                    error=error_msg,
                )
                db.add(call_log)
                db.flush()
            raise IcsError(error_msg, retryable=True) from e

    def add_task(self, payload: dict[str, Any], endpoint_path: str = "/amr/submitMission") -> dict[str, Any]:
        """Backward-compatibility bridge for raw task dispatching."""
        return self._post_kuka(endpoint_path, payload, api_name="raw_submitMission")

    def fleet_container_in(
        self,
        location_code: str,
        container_code: str,
        is_new: bool = False,
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET API - POST /amr/containerIn]
        Register presence of physical container (`container_code`) at location (`location_code`).
        """
        request_id = f"CIN{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "containerCode": container_code,
            "enterOrientation": "",
            "isNew": is_new,
            "position": location_code,
            "requestId": request_id,
        }
        logger.info("Fleet containerIn: container=%s at position=%s isNew=%s", container_code, location_code, is_new)
        return self._post_kuka(
            "/amr/containerIn",
            payload,
            api_name="containerIn",
            container_code=container_code,
            request_id=request_id,
            db=db,
        )

    def fleet_insert_rack(self, location_code: str, container_code: str, db: Optional[Session] = None) -> dict[str, Any]:
        """Alias for fleet_container_in."""
        return self.fleet_container_in(location_code, container_code, db=db)

    def fleet_container_out(
        self,
        location_code: str = "",
        container_code: str = "",
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET API - POST /amr/containerOut]
        De-register physical container (`container_code`) when returned to Empty Cart Buffer.
        """
        request_id = f"COUT{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "requestId": request_id,
            "containerType": "",
            "containerCode": container_code,
            "position": location_code,
            "isDelete": False,
        }
        logger.info("Fleet containerOut: container=%s at position=%s", container_code, location_code)
        return self._post_kuka(
            "/amr/containerOut",
            payload,
            api_name="containerOut",
            container_code=container_code,
            request_id=request_id,
            db=db,
        )

    def fleet_remove_rack(self, location_code: str, container_code: str) -> dict[str, Any]:
        """Alias for fleet_container_out."""
        return self.fleet_container_out(location_code=location_code, container_code=container_code)

    def fleet_cancel_task(self, mission_code: str) -> dict[str, Any]:
        """
        [FLEET API - POST /amr/missionCancel]
        Cancel an active Fleet task by `missionCode`.
        """
        request_id = f"CXL{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "requestId": request_id,
            "missionCode": mission_code,
            "containerCode": "",
            "position": "",
            "cancelMode": "FORCE",
        }
        return self._post_kuka(
            "/amr/missionCancel",
            payload,
            api_name="missionCancel",
            mission_code=mission_code,
            request_id=request_id,
        )

    def fleet_move_material(
        self,
        task: FleetTask,
        pickup_code: str,
        dropoff_code: str,
        container_code: Optional[str],
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET MOVE 1 - Raw Material -> CNC or CNC Level N -> CNC Level N+1]
        Dispatches AMR via POST /amr/submitMission with 2 waypoints.
        """
        org_id = getattr(settings, "kuka_org_id", "KUKA011021")
        container_model = getattr(settings, "kuka_container_model_code", "1001")
        robot_type = getattr(settings, "kuka_robot_type", "LIFT")
        mission_type = getattr(settings, "kuka_mission_type", "RACK_MOVE")

        req_id = task.fleet_request_id or f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        task.fleet_request_id = req_id

        mission_data = [
            {
                "sequence": 1,
                "position": pickup_code,
                "type": "NODE_POINT",
                "putDown": False,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
            {
                "sequence": 2,
                "position": dropoff_code,
                "type": "NODE_POINT",
                "putDown": True,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
        ]
        task.mission_data = mission_data
        task.container_code = container_code

        payload = {
            "orgId": org_id,
            "requestId": req_id,
            "missionCode": task.mission_code,
            "missionType": mission_type,
            "viewBoardType": "",
            "robotModels": [],
            "robotIds": [],
            "robotType": robot_type,
            "priority": 1,
            "containerModelCode": container_model,
            "templateCode": "",
            "lockRobotAfterFinish": False,
            "unlockRobotId": "",
            "unlockMissionCode": "",
            "idleNode": "",
            "missionData": mission_data,
        }
        return self._post_kuka(
            "/amr/submitMission",
            payload,
            api_name="submitMission:material",
            mission_code=task.mission_code,
            container_code=container_code,
            request_id=req_id,
            db=db,
        )

    def fleet_move_to_wash(
        self,
        task: FleetTask,
        pickup_code: str,
        wash_code: str,
        container_code: Optional[str],
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET MOVE 2 - Final CNC -> Washing Station]
        Dispatches AMR via POST /amr/submitMission with 2 waypoints.
        """
        org_id = getattr(settings, "kuka_org_id", "KUKA011021")
        container_model = getattr(settings, "kuka_container_model_code", "1001")
        robot_type = getattr(settings, "kuka_robot_type", "LIFT")
        mission_type = getattr(settings, "kuka_mission_type", "RACK_MOVE")

        req_id = task.fleet_request_id or f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        task.fleet_request_id = req_id

        mission_data = [
            {
                "sequence": 1,
                "position": pickup_code,
                "type": "NODE_POINT",
                "putDown": False,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
            {
                "sequence": 2,
                "position": wash_code,
                "type": "NODE_POINT",
                "putDown": False,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
        ]
        task.mission_data = mission_data
        task.container_code = container_code

        payload = {
            "orgId": org_id,
            "requestId": req_id,
            "missionCode": task.mission_code,
            "missionType": mission_type,
            "viewBoardType": "",
            "robotModels": [],
            "robotIds": [],
            "robotType": robot_type,
            "priority": 1,
            "containerModelCode": container_model,
            "templateCode": "",
            "lockRobotAfterFinish": True,
            "unlockRobotId": "",
            "unlockMissionCode": "",
            "idleNode": "",
            "missionData": mission_data,
        }
        return self._post_kuka(
            "/amr/submitMission",
            payload,
            api_name="submitMission:wash",
            mission_code=task.mission_code,
            container_code=container_code,
            request_id=req_id,
            db=db,
        )

    def fleet_move_empty_container(
        self,
        task: FleetTask,
        pickup_code: str,
        buffer_code: str,
        container_code: Optional[str],
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET MOVE 3 - Washing Station -> Empty Cart Buffer]
        Dispatches AMR via POST /amr/submitMission to return empty container.
        """
        org_id = getattr(settings, "kuka_org_id", "KUKA011021")
        container_model = getattr(settings, "kuka_container_model_code", "1001")
        robot_type = getattr(settings, "kuka_robot_type", "LIFT")
        mission_type = getattr(settings, "kuka_mission_type", "RACK_MOVE")

        req_id = task.fleet_request_id or f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        task.fleet_request_id = req_id

        mission_data = [
            {
                "sequence": 1,
                "position": pickup_code,
                "type": "NODE_POINT",
                "putDown": False,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
            {
                "sequence": 2,
                "position": buffer_code,
                "type": "NODE_POINT",
                "putDown": True,
                "passStrategy": "AUTO",
                "waitingMillis": 0,
            },
        ]
        task.mission_data = mission_data
        task.container_code = container_code

        payload = {
            "orgId": org_id,
            "requestId": req_id,
            "missionCode": task.mission_code,
            "missionType": mission_type,
            "viewBoardType": "",
            "robotModels": [],
            "robotIds": [],
            "robotType": robot_type,
            "priority": 1,
            "containerModelCode": container_model,
            "templateCode": "",
            "lockRobotAfterFinish": False,
            "unlockRobotId": "",
            "unlockMissionCode": "",
            "idleNode": "",
            "missionData": mission_data,
        }
        return self._post_kuka(
            "/amr/submitMission",
            payload,
            api_name="submitMission:empty_container",
            mission_code=task.mission_code,
            container_code=container_code,
            request_id=req_id,
            db=db,
        )

    def fleet_move_empty_rack(
        self,
        task: FleetTask,
        pickup_code: str,
        buffer_code: str,
        container_code: Optional[str],
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """Alias for fleet_move_empty_container."""
        return self.fleet_move_empty_container(task, pickup_code, buffer_code, container_code, db=db)

    def submit_fleet_task(self, db: Session, task: FleetTask, request_type: str = "CALL_MATERIAL") -> FleetTask:
        """Submit an already-persisted FleetTask to KUKA Fleet Manager via submitMission."""
        pickup_loc = db.query(Location).filter(Location.id == task.pickup_location_id).first()
        dropoff_loc = db.query(Location).filter(Location.id == task.dropoff_location_id).first()
        if not pickup_loc or not dropoff_loc:
            error_msg = f"Vị trí lấy/hạ hàng không tồn tại (pickup={task.pickup_location_id}, dropoff={task.dropoff_location_id})"
            logger.error(error_msg)
            task.status = "failed"
            task.error_message = error_msg
            db.flush()
            return task

        pickup_code = pickup_loc.location_code
        dropoff_code = dropoff_loc.location_code
        c_code = task.container_code

        try:
            if request_type in ("MOVE_TO_WASH", "SEND_TO_WASH"):
                self.fleet_move_to_wash(task, pickup_code, dropoff_code, c_code, db=db)
            elif request_type == "RETURN_EMPTY_CART":
                self.fleet_move_empty_container(task, pickup_code, dropoff_code, c_code, db=db)
            else:
                self.fleet_move_material(task, pickup_code, dropoff_code, c_code, db=db)

            task.status = "sent"
            task.sent_at = datetime.now(timezone.utc)
            db.flush()
        except IcsError as e:
            logger.warning("Could not submit task %s to Fleet: %s", task.mission_code, e)
            task.submit_attempts += 1
            task.error_message = str(e)

            # Bất kỳ lỗi IcsError nào khi submitMission đều đánh dấu FAILED và giải phóng khóa xe,
            # tránh để xe bị kẹt hay treo trạng thái giả lập.
            task.status = "failed"
            if task.container:
                task.container.is_locked = False
                task.container.locked_by_mission_code = None
                task.container.destination_location_id = None
            if task.request:
                task.request.status = "failed"
                task.request.error_message = str(e)

            db.flush()
        return task
