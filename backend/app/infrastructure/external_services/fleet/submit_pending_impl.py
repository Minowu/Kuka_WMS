"""Submit pending FleetTask to KUKA — extracted from Celery worker."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.core.database import db_session
from app.core.logger import get_logger
from app.modules.production.dispatch.kuka_fleet_client import (
    IcsError,
    KukaFleetClient,
    fail_and_release,
)
from app.modules.production.dispatch_service import dispatch_service
from app.modules.production.production_models import FleetApiCall, FleetTask
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("main")
MAX_FLEET_SUBMIT_ATTEMPTS = 5
_fleet_client = KukaFleetClient()


def run_submit_pending_fleet_task(fleet_task_id: int) -> Optional[dict[str, Any]]:
    """
    Worker gửi nhiệm vụ sang KUKA Fleet bất đồng bộ, tách biệt nghiêm ngặt thành 3 bước để không giữ kết nối DB:
    - Bước 1 (Mở DB Session ngắn): Dùng Compare-And-Set (CAS) chuyển `pending_submit -> submitting`,
      đọc thông tin vị trí lấy/hạ hàng và mã xe phôi, sau đó COMMIT và ĐÓNG ngay kết nối DB.
    - Bước 2 (Không giữ DB Session): Thực hiện gọi HTTP POST sang KUKA Fleet Manager.
    - Bước 3 (Mở DB Session mới): Lưu bảng kiểm toán `FleetApiCall` và dùng CAS chuyển `submitting -> sent`
      (hoặc tăng số lần thử retry / gọi `fail_and_release` mở khóa xe nếu lỗi vĩnh viễn hoặc quá số lần thử).
    """
    # -------------------------------------------------------------------------
    # BƯỚC 1: Nhận task bằng câu lệnh nguyên tử CAS (pending_submit -> submitting) & đọc dữ liệu
    # -------------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    with db_session() as db:
        claimed_rows = (
            db.query(FleetTask)
            .filter(
                FleetTask.id == fleet_task_id,
                FleetTask.status == "pending_submit",
            )
            .update(
                {"status": "submitting", "updated_at": now},
                synchronize_session=False,
            )
        )
        db.commit()
        if claimed_rows != 1:
            logger.info(
                "Skipping submit_fleet_task(id=%s): not in 'pending_submit' state (claimed=%s)",
                fleet_task_id,
                claimed_rows,
            )
            return {"skipped": True, "fleet_task_id": fleet_task_id}

        task = db.query(FleetTask).filter(FleetTask.id == fleet_task_id).first()
        if not task:
            return {"skipped": True, "fleet_task_id": fleet_task_id}

        pickup_loc = db.query(Location).filter(Location.id == task.pickup_location_id).first()
        dropoff_loc = db.query(Location).filter(Location.id == task.dropoff_location_id).first()
        if not pickup_loc or not dropoff_loc:
            error_msg = (
                f"Vị trí lấy/hạ hàng không tồn tại "
                f"(pickup={task.pickup_location_id}, dropoff={task.dropoff_location_id})"
            )
            logger.error(error_msg)
            fail_and_release(db, task, error_msg)
            db.commit()
            return {"status": "failed", "fleet_task_id": fleet_task_id, "error": error_msg}

        mission_code = task.mission_code
        fleet_req_id = task.fleet_request_id
        pickup_loc_id = task.pickup_location_id
        dropoff_loc_id = task.dropoff_location_id
        pickup_code = pickup_loc.location_code
        dropoff_code = dropoff_loc.location_code
        container_code = task.container_code
        created_by = task.request.created_by if task.request else None
        request_type = task.request.request_type if task.request else None

        event_loc_ids = sorted({int(lid) for lid in (pickup_loc_id, dropoff_loc_id) if lid is not None})
        recipient_user_ids = resolve_location_recipient_user_ids(
            db,
            event_loc_ids,
            extra_user_ids=[created_by],
        )

        req_id, api_name, mission_data, payload = _fleet_client.build_mission_payload(
            mission_code=mission_code,
            fleet_request_id=fleet_req_id,
            pickup_code=pickup_code,
            dropoff_code=dropoff_code,
            container_code=container_code,
            request_type=request_type,
        )
        task.fleet_request_id = req_id
        task.mission_data = mission_data
        db.commit()

    # -------------------------------------------------------------------------
    # BƯỚC 2: Gọi HTTP thuần sang KUKA Fleet (HOÀN TOÀN KHÔNG giữ kết nối DB!)
    # -------------------------------------------------------------------------
    call_error: Optional[IcsError] = None
    audit_log: Optional[dict[str, Any]] = None
    try:
        _, audit_log = _fleet_client._do_fleet_call(
            endpoint_path="/amr/submitMission",
            payload=payload,
            api_name=api_name,
            mission_code=mission_code,
            container_code=container_code,
            request_id=req_id,
        )
    except IcsError as exc:
        call_error = exc
        audit_log = getattr(exc, "audit_log", None)
    except Exception as exc:
        call_error = IcsError(f"Unexpected Fleet error: {exc}", retryable=True)

    # -------------------------------------------------------------------------
    # BƯỚC 3: Mở kết nối DB mới để ghi log kiểm toán & cập nhật trạng thái nhiệm vụ
    # -------------------------------------------------------------------------
    should_retry = False
    retry_countdown = 5
    final_status = "sent"

    with db_session() as db:
        if audit_log:
            existing_call = (
                db.query(FleetApiCall)
                .filter(FleetApiCall.request_id == audit_log["request_id"])
                .first()
            )
            if existing_call:
                existing_call.http_status = audit_log.get("http_status")
                existing_call.response_body = audit_log.get("response_body")
                existing_call.success = bool(audit_log.get("success"))
                existing_call.error = audit_log.get("error")
            else:
                db.add(FleetApiCall(**audit_log))

        if call_error is None:
            # Quy tắc 2: Chỉ chuyển từ 'submitting' -> 'sent' bằng CAS để KHÔNG BAO GIỜ ghi đè lùi
            # nếu Webhook từ KUKA Fleet đã đến sớm hơn và đẩy task sang 'in_progress' / 'completed'!
            sent_now = datetime.now(timezone.utc)
            db.query(FleetTask).filter(
                FleetTask.id == fleet_task_id,
                FleetTask.status == "submitting",
            ).update(
                {
                    "status": "sent",
                    "sent_at": sent_now,
                    "error_message": None,
                    "updated_at": sent_now,
                },
                synchronize_session=False,
            )
            db.commit()
            publish_event(
                "floor.changed",
                {
                    "reason": "task_sent",
                    "mission_code": mission_code,
                    "location_ids": event_loc_ids,
                },
                user_ids=recipient_user_ids,
                admins=True,
            )
            return {"status": "sent", "fleet_task_id": fleet_task_id, "mission_code": mission_code}

        # Nhánh xử lý khi gọi KUKA Fleet gặp lỗi
        task = (
            db.query(FleetTask)
            .filter(FleetTask.id == fleet_task_id)
            .with_for_update(of=FleetTask)
            .first()
        )
        if not task:
            db.commit()
            return None

        # Nếu Webhook đã đẩy task sang 'in_progress' hoặc 'completed' thì tuyệt đối không đánh dấu lỗi!
        if task.status in ("in_progress", "completed"):
            db.commit()
            return {"status": task.status, "fleet_task_id": fleet_task_id}

        task.submit_attempts = (task.submit_attempts or 0) + 1
        task.error_message = str(call_error)
        is_retryable = bool(getattr(call_error, "retryable", True))

        if not is_retryable or task.submit_attempts >= MAX_FLEET_SUBMIT_ATTEMPTS:
            fail_and_release(db, task, str(call_error))
            final_status = "failed"
            db.commit()
            # Quét lại hàng đợi để các yêu cầu đang chờ khác có thể lấy xe vừa được mở khóa
            try:
                dispatch_service.scan_all_transport_queues(db)
            except Exception as q_exc:
                logger.warning("Queue scan after fail_and_release warning: %s", q_exc)
        else:
            task.status = "pending_submit"
            task.updated_at = datetime.now(timezone.utc)
            final_status = "pending_submit"
            should_retry = True
            retry_countdown = min(5 * (2 ** max(task.submit_attempts - 1, 0)), 60)
            db.commit()

    result = {"status": final_status, "fleet_task_id": fleet_task_id, "error": str(call_error)}
    if should_retry:
        result["_should_retry"] = True
        result["_retry_countdown"] = retry_countdown
        result["_retry_exc"] = call_error
    return result


