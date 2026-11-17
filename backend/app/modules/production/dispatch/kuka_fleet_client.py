"""KUKA Fleet Manager (ICS/RCS) HTTP Adapter & Command Hooks."""

from datetime import datetime, timezone
from typing import Any, Optional, Union
import time
import uuid

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import bind_context, get_logger
from app.modules.production.dispatch.fleet_task_release import fail_and_release
from app.modules.production.dispatch.ics_errors import IcsError, _ics_configured
from app.modules.production.production_models import (
    FleetApiCall,
    FleetTask,
    ProductionRoute,
    RouteStep,
    TransportQueue,
)
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import resolve_location_recipient_user_ids, schedule_event_after_commit

logger = get_logger("wms.fleet.out")

__all__ = ["KukaFleetClient", "IcsError", "fail_and_release", "_ics_configured"]

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
        task_id: Optional[Union[int, str]] = None,
    ) -> dict[str, Any]:
        """Low-level HTTP POST to KUKA Fleet Manager with audit logging in fleet_api_call."""
        req_id = request_id or str(payload.get("requestId") or f"REQ_{uuid.uuid4().hex[:12].upper()}")
        resolved_task_id = task_id or payload.get("taskId") or payload.get("task_id")
        ctx_to_bind: dict[str, Any] = {"fleet_request_id": req_id}
        if resolved_task_id is not None:
            ctx_to_bind["fleet_task_id"] = resolved_task_id
            ctx_to_bind["task_id"] = resolved_task_id
        bind_context(**ctx_to_bind)

        base = (getattr(settings, "kuka_base_url", None) or "").strip().rstrip("/")
        endpoint = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        url = f"{base}{endpoint}"

        start_time = time.perf_counter()
        duration_ms = 0.0

        if not _ics_configured():
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_msg = f"KUKA Fleet API chưa được cấu hình hoặc offline — không thể điều xe {api_name}"
            logger.error(
                "KUKA Fleet unconfigured: %s (url=%s, fleet_request_id=%s)",
                error_msg,
                url,
                req_id,
                extra={
                    "url": url,
                    "fleet_request_id": req_id,
                    "payload": payload,
                    "http_status": 503,
                    "duration_ms": duration_ms,
                },
            )
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

        timeout_sec = float(getattr(settings, "kuka_http_timeout_seconds", 8.0))
        http_status = None
        headers = {
            "Content-Type": "application/json",
            "orgId": getattr(settings, "kuka_org_id", "KUKA011021"),
        }
        token = getattr(settings, "kuka_access_token", None) or getattr(settings, "kuka_api_token", None)
        if token:
            headers["Authorization"] = token

        connect_timeout = min(3.0, timeout_sec)
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout_sec, connect=connect_timeout)) as client:
                response = client.post(url, json=payload, headers=headers)
                http_status = response.status_code
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                response.raise_for_status()
                resp_data = response.json()

            logger.info(
                "Fleet POST %s [%s] url=%s status=%s duration_ms=%.2f",
                endpoint_path,
                api_name,
                url,
                http_status,
                duration_ms,
                extra={
                    "url": url,
                    "fleet_request_id": req_id,
                    "payload": payload,
                    "http_status": http_status,
                    "duration_ms": duration_ms,
                },
            )

            fleet_success = resp_data.get("success") is True and str(resp_data.get("code", "")) in ("0", "200")
            fleet_code = str(resp_data.get("code", ""))
            fleet_msg = resp_data.get("message")

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
                logger.warning(
                    err_text,
                    extra={
                        "url": url,
                        "fleet_request_id": req_id,
                        "payload": payload,
                        "http_status": http_status,
                        "duration_ms": duration_ms,
                    },
                )
                raise IcsError(err_text, retryable=False)

            return resp_data
        except httpx.HTTPStatusError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            http_status = e.response.status_code
            error_msg = f"KUKA Fleet server error ({http_status}): {e.response.text}"
            if http_status >= 500:
                logger.error(
                    "KUKA Fleet HTTP %s error (url=%s, duration_ms=%.2f): %s",
                    http_status,
                    url,
                    duration_ms,
                    error_msg,
                    exc_info=True,
                    extra={
                        "url": url,
                        "fleet_request_id": req_id,
                        "payload": payload,
                        "http_status": http_status,
                        "duration_ms": duration_ms,
                    },
                )
            else:
                logger.warning(
                    "KUKA Fleet HTTP %s warning (url=%s, duration_ms=%.2f): %s",
                    http_status,
                    url,
                    duration_ms,
                    error_msg,
                    exc_info=True,
                    extra={
                        "url": url,
                        "fleet_request_id": req_id,
                        "payload": payload,
                        "http_status": http_status,
                        "duration_ms": duration_ms,
                    },
                )
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
        except httpx.TimeoutException as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_msg = f"KUKA Fleet timeout connecting to {url}: {e}"
            logger.warning(
                error_msg,
                exc_info=True,
                extra={
                    "url": url,
                    "fleet_request_id": req_id,
                    "payload": payload,
                    "http_status": None,
                    "duration_ms": duration_ms,
                },
            )
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
        except httpx.RequestError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_msg = f"Cannot reach KUKA Fleet server ({url}): {e}"
            logger.warning(
                error_msg,
                exc_info=True,
                extra={
                    "url": url,
                    "fleet_request_id": req_id,
                    "payload": payload,
                    "http_status": None,
                    "duration_ms": duration_ms,
                },
            )
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

    # Alias _post to _post_kuka for general / client callers
    _post = _post_kuka

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

    def fleet_container_query(
        self,
        container_code: str = "",
        node_code: str = "",
        area_code: str = "",
        empty_full_status: int = 2,
        container_model_code: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        [FLEET API - POST /amr/containerQuery]
        Tra cứu container đang có trên bản đồ Fleet theo `containerCode` (và các filter tùy chọn).
        """
        model_code = (
            container_model_code
            or getattr(settings, "kuka_container_model_code", None)
            or "CNC_TROLLEY_001"
        )
        payload = {
            "nodeCode": node_code or "",
            "containerModelCode": model_code,
            "containerCode": container_code or "",
            "areaCode": area_code or "",
            "emptyFullStatus": empty_full_status,
        }
        logger.info(
            "Fleet containerQuery: container=%s model=%s emptyFullStatus=%s",
            container_code,
            model_code,
            empty_full_status,
        )
        return self._post_kuka(
            "/amr/containerQuery",
            payload,
            api_name="containerQuery",
            container_code=container_code or None,
            db=db,
        )

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
            task_id=task.id,
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
            task_id=task.id,
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
            task_id=task.id,
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


    def build_mission_payload(self, *args, **kwargs):
        from app.modules.production.dispatch.fleet_task_submit import build_mission_payload

        return build_mission_payload(self, *args, **kwargs)

    def _do_fleet_call(self, *args, **kwargs):
        from app.modules.production.dispatch.fleet_task_submit import _do_fleet_call

        return _do_fleet_call(self, *args, **kwargs)

    def submit_fleet_task(self, *args, **kwargs):
        from app.modules.production.dispatch.fleet_task_submit import submit_fleet_task

        return submit_fleet_task(self, *args, **kwargs)
