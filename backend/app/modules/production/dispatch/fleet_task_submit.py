"""Fleet mission payload build + submit (extracted from KukaFleetClient)."""

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
from app.modules.production.production_models import FleetTask
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("wms.fleet.out")


def build_mission_payload(
    client,
    mission_code: str,
    fleet_request_id: Optional[str],
    pickup_code: str,
    dropoff_code: str,
    container_code: Optional[str],
    request_type: Optional[str] = None,
) -> tuple[str, str, list[dict[str, Any]], dict[str, Any]]:
    """
    Tạo dữ liệu `(req_id, api_name, mission_data, payload)` cho API `/amr/submitMission` mà không cần giữ kết nối DB.
    Giữ nguyên `fleet_request_id` qua các lần retry để đảm bảo tính chống trùng lặp (idempotency) bên phía KUKA Fleet.
    """
    org_id = getattr(settings, "kuka_org_id", "KUKA011021")
    container_model = getattr(settings, "kuka_container_model_code", "1001")
    robot_type = getattr(settings, "kuka_robot_type", "LIFT")
    mission_type = getattr(settings, "kuka_mission_type", "RACK_MOVE")

    req_id = fleet_request_id or f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"

    if request_type in ("MOVE_TO_WASH", "SEND_TO_WASH"):
        put_down_dropoff = False
        lock_robot = True
        api_name = "submitMission:wash"
    elif request_type == "RETURN_EMPTY_CART":
        put_down_dropoff = True
        lock_robot = False
        api_name = "submitMission:empty_container"
    else:
        put_down_dropoff = True
        lock_robot = False
        api_name = "submitMission:material"

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
            "putDown": put_down_dropoff,
            "passStrategy": "AUTO",
            "waitingMillis": 0,
        },
    ]

    payload = {
        "orgId": org_id,
        "requestId": req_id,
        "missionCode": mission_code,
        "missionType": mission_type,
        "viewBoardType": "",
        "robotModels": [],
        "robotIds": [],
        "robotType": robot_type,
        "priority": 1,
        "containerModelCode": container_model,
        "templateCode": "",
        "lockRobotAfterFinish": lock_robot,
        "unlockRobotId": "",
        "unlockMissionCode": "",
        "idleNode": "",
        "missionData": mission_data,
    }
    return req_id, api_name, mission_data, payload


def _do_fleet_call(
    client,
    endpoint_path: str,
    payload: dict[str, Any],
    api_name: str,
    mission_code: Optional[str] = None,
    container_code: Optional[str] = None,
    request_id: Optional[str] = None,
    task_id: Optional[Union[int, str]] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Thực hiện gọi HTTP POST thuần tới KUKA Fleet Manager MÀ KHÔNG giữ kết nối Database.
    Trả về `(response_data, audit_log_dict)` nếu gửi thành công.
    Nếu thất bại, đính kèm thông tin nhật ký `e.audit_log` vào ngoại lệ `IcsError` và ném lỗi ra ngoài.
    """
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
        err = IcsError(error_msg, retryable=True)
        err.audit_log = {
            "api_name": api_name,
            "request_id": req_id,
            "mission_code": mission_code,
            "container_code": container_code,
            "request_body": payload,
            "http_status": 503,
            "response_body": err_resp,
            "error": error_msg,
            "success": False,
        }
        raise err

    timeout_sec = float(getattr(settings, "kuka_http_timeout_seconds", 5.0))
    connect_timeout = min(2.0, timeout_sec)
    headers = {
        "Content-Type": "application/json",
        "orgId": getattr(settings, "kuka_org_id", "KUKA011021"),
    }
    token = getattr(settings, "kuka_access_token", None) or getattr(settings, "kuka_api_token", None)
    if token:
        headers["Authorization"] = token

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

        audit_log = {
            "api_name": api_name,
            "request_id": req_id,
            "mission_code": mission_code,
            "container_code": container_code,
            "request_body": payload,
            "http_status": http_status,
            "response_body": resp_data,
            "success": fleet_success,
            "error": fleet_msg if not fleet_success else None,
        }

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
            err = IcsError(err_text, retryable=False)
            err.audit_log = audit_log
            raise err

        return resp_data, audit_log
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
        err = IcsError(error_msg, retryable=(http_status >= 500))
        err.audit_log = {
            "api_name": api_name,
            "request_id": req_id,
            "mission_code": mission_code,
            "container_code": container_code,
            "request_body": payload,
            "http_status": http_status,
            "response_body": None,
            "success": False,
            "error": error_msg,
        }
        raise err from e
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
        err = IcsError(error_msg, retryable=True)
        err.audit_log = {
            "api_name": api_name,
            "request_id": req_id,
            "mission_code": mission_code,
            "container_code": container_code,
            "request_body": payload,
            "http_status": None,
            "response_body": None,
            "success": False,
            "error": error_msg,
        }
        raise err from e
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
        err = IcsError(error_msg, retryable=True)
        err.audit_log = {
            "api_name": api_name,
            "request_id": req_id,
            "mission_code": mission_code,
            "container_code": container_code,
            "request_body": payload,
            "http_status": None,
            "response_body": None,
            "success": False,
            "error": error_msg,
        }
        raise err from e


def submit_fleet_task(client, db: Session, task: FleetTask, request_type: Optional[str] = None) -> FleetTask:
    """Submit an already-persisted FleetTask to KUKA Fleet Manager via submitMission."""
    pickup_loc = db.query(Location).filter(Location.id == task.pickup_location_id).first()
    dropoff_loc = db.query(Location).filter(Location.id == task.dropoff_location_id).first()
    if not pickup_loc or not dropoff_loc:
        error_msg = f"Vị trí lấy/hạ hàng không tồn tại (pickup={task.pickup_location_id}, dropoff={task.dropoff_location_id})"
        logger.error(error_msg)
        return fail_and_release(db, task, error_msg)

    if request_type is None and task.request:
        request_type = task.request.request_type

    pickup_code = pickup_loc.location_code
    dropoff_code = dropoff_loc.location_code
    c_code = task.container_code

    try:
        bind_context(fleet_task_id=task.id, task_id=task.id)
        if request_type in ("MOVE_TO_WASH", "SEND_TO_WASH"):
            client.fleet_move_to_wash(task, pickup_code, dropoff_code, c_code, db=db)
        elif request_type == "RETURN_EMPTY_CART":
            client.fleet_move_empty_container(task, pickup_code, dropoff_code, c_code, db=db)
        else:
            client.fleet_move_material(task, pickup_code, dropoff_code, c_code, db=db)

        task.status = "sent"
        task.sent_at = datetime.now(timezone.utc)
        db.flush()
    except IcsError as e:
        logger.warning(
            "Could not submit task %s to Fleet: %s (retryable=%s)",
            task.mission_code,
            e,
            getattr(e, "retryable", True),
            exc_info=True,
            extra={
                "fleet_task_id": task.id,
                "mission_code": task.mission_code,
                "retryable": getattr(e, "retryable", True),
            },
        )
        task.submit_attempts += 1
        task.error_message = str(e)

        if not getattr(e, "retryable", True):
            fail_and_release(db, task, str(e))
        else:
            task.status = "pending_submit"
            db.flush()
    return task
