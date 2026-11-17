"""Business logic for Admin Container / Rack Management & Transport Request Cancellation."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import bind_context, get_logger
from app.modules.auth.auth_model import User
from app.modules.production.dispatch.service import dispatch_service
from app.modules.production.production_models import (
    FleetTask,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportQueue,
    TransportRequest,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.dispatch")

ACTIVE_TASK_STATUSES = ("created", "pending_submit", "submitting", "sent", "dispatched", "in_progress")
ACTIVE_REQUEST_STATUSES = ("pending", "queued_for_cart", "queued_for_slot", "in_progress")
from app.modules.production.rack.policy import _ensure_rack_modifiable
from app.modules.production.rack.query import serialize_rack

def _fleet_query_hits_for_container(query_resp: dict[str, Any], container_code: str) -> list[dict[str, Any]]:
    """Lọc các bản ghi Fleet `containerQuery` khớp đúng `containerCode` (không phụ thuộc nodeCode)."""
    raw = query_resp.get("data") if isinstance(query_resp, dict) else None
    if not isinstance(raw, list):
        return []
    target = (container_code or "").strip()
    hits: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        code = str(row.get("containerCode") or row.get("container_code") or "").strip()
        if code == target:
            hits.append(row)
    return hits

def remove_rack_container(
    db: Session,
    rack_id: int,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Xóa / thu hồi Container (Rack) — phạm vi A (Admin xóa tay trên Rack Management):
    1. Chặn nếu Rack đang khóa / có FleetTask / TransportRequest active.
    2. Luôn `POST /amr/containerQuery` theo `containerCode` (không phụ thuộc `fleet_registered`).
       - Query lỗi / timeout: giữ nguyên WMS.
       - `data` rỗng: coi như không còn trên Fleet → thu hồi WMS.
       - Có bản ghi và `isCarry=1`: chặn xóa.
       - Có bản ghi và không đang mang: `containerOut` rồi mới thu hồi WMS.
       - `containerOut` lỗi thật: giữ nguyên WMS.
    """
    cart = (
        db.query(ItemStock)
        .options(joinedload(ItemStock.item))
        .filter(ItemStock.id == rack_id)
        .with_for_update(of=ItemStock)
        .first()
    )
    if not cart:
        raise ValueError(f"Không tìm thấy Rack (ID={rack_id}).")

    _ensure_rack_modifiable(db, cart, "xóa", require_relocatable=False)

    old_loc_id = cart.location_id
    loc = db.query(Location).filter(Location.id == old_loc_id).first() if old_loc_id else None
    loc_code = (loc.location_code or "").strip() if loc else ""
    loc_display = (loc.location_name or loc.location_code) if loc else "Bãi trống / Chưa rõ vị trí"
    c_code = (cart.container_code or "").strip()

    if not c_code:
        raise ValueError("Rack không có mã container_code hợp lệ.")

    bind_context(container_code=c_code, station_code=loc_code or None)

    logger.info(
        "[remove_rack] step=1_start rack_id=%s container=%s loc=%s loc_code=%s "
        "fleet_registered=%s status=%s is_active=%s operator_id=%s",
        rack_id,
        c_code,
        loc_display,
        loc_code or None,
        bool(cart.fleet_registered),
        cart.status,
        bool(cart.is_active),
        operator_id,
    )

    called_fleet_out = False
    skipped_fleet_absent = False

    logger.info(
        "[remove_rack] step=2_containerQuery_request container=%s emptyFullStatus=2",
        c_code,
    )
    try:
        query_resp = dispatch_service.fleet_container_query(
            container_code=c_code,
            empty_full_status=2,
            db=db,
        )
    except Exception as e:
        db.commit()
        logger.error(
            "[remove_rack] step=2_containerQuery_FAIL container=%s error=%s — giữ nguyên WMS",
            c_code,
            e,
            exc_info=True,
        )
        raise ValueError(
            f"Không thể xóa Rack '{c_code}' vì không truy vấn được trạng thái trên KUKA Fleet "
            f"(containerQuery lỗi/timeout). WMS giữ nguyên. Chi tiết: {e}"
        ) from e

    raw_data = query_resp.get("data") if isinstance(query_resp, dict) else None
    raw_count = len(raw_data) if isinstance(raw_data, list) else None
    logger.info(
        "[remove_rack] step=2_containerQuery_OK container=%s fleet_success=%s fleet_code=%s "
        "raw_data_count=%s",
        c_code,
        query_resp.get("success") if isinstance(query_resp, dict) else None,
        query_resp.get("code") if isinstance(query_resp, dict) else None,
        raw_count,
    )

    hits = _fleet_query_hits_for_container(query_resp, c_code)
    logger.info(
        "[remove_rack] step=3_match_hits container=%s matched_count=%s hits=%s",
        c_code,
        len(hits),
        [
            {
                "containerCode": h.get("containerCode") or h.get("container_code"),
                "nodeCode": h.get("nodeCode") or h.get("node_code"),
                "isCarry": h.get("isCarry", h.get("is_carry")),
                "inMapStatus": h.get("inMapStatus", h.get("in_map_status")),
                "emptyFullStatus": h.get("emptyFullStatus", h.get("empty_full_status")),
            }
            for h in hits
        ],
    )

    if not hits:
        skipped_fleet_absent = True
        logger.info(
            "[remove_rack] step=4_decision SKIP_containerOut reason=query_empty "
            "container=%s → sẽ thu hồi WMS",
            c_code,
        )
    else:
        carrying = [
            h for h in hits
            if str(h.get("isCarry", h.get("is_carry", "0"))).strip() in ("1", "true", "True")
        ]
        if carrying:
            logger.warning(
                "[remove_rack] step=4_decision BLOCK reason=isCarry=1 container=%s carrying=%s "
                "— giữ nguyên WMS",
                c_code,
                carrying,
            )
            raise ValueError(
                f"Không thể xóa Rack '{c_code}': KUKA Fleet báo container đang được AMR mang "
                f"(isCarry=1). Hãy đợi nhiệm vụ kết thúc rồi thử lại."
            )

        # position chỉ để gửi Out; sự tồn tại đã xác định bằng containerCode
        out_position = loc_code
        if not out_position:
            out_position = str(hits[0].get("nodeCode") or hits[0].get("node_code") or "").strip()

        logger.info(
            "[remove_rack] step=4_decision CALL_containerOut container=%s position=%s "
            "(wms_loc_code=%s)",
            c_code,
            out_position or None,
            loc_code or None,
        )
        try:
            dispatch_service.fleet_container_out(
                location_code=out_position,
                container_code=c_code,
                db=db,
            )
            called_fleet_out = True
            logger.info(
                "[remove_rack] step=5_containerOut_OK container=%s position=%s",
                c_code,
                out_position or None,
            )
        except Exception as e:
            db.commit()
            logger.error(
                "[remove_rack] step=5_containerOut_FAIL container=%s position=%s error=%s "
                "— giữ nguyên WMS",
                c_code,
                out_position or None,
                e,
                exc_info=True,
            )
            raise ValueError(
                f"Không thể xóa Rack '{c_code}' tại vị trí '{loc_display}' vì KUKA Fleet báo lỗi "
                f"containerOut: {e}"
            ) from e

    logger.info(
        "[remove_rack] step=6_wms_deactivate_begin container=%s called_fleet_out=%s "
        "skipped_fleet_absent=%s",
        c_code,
        called_fleet_out,
        skipped_fleet_absent,
    )

    cart.location_id = None
    cart.destination_location_id = None
    cart.quantity = 0
    cart.current_stage_level = 0
    cart.status = "empty"
    cart.is_active = False
    cart.is_locked = False
    cart.locked_by_mission_code = None
    cart.fleet_registered = False

    loc_ids = [int(old_loc_id)] if old_loc_id is not None else []
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[operator_id],
    )

    db.commit()
    db.refresh(cart)

    logger.info(
        "[remove_rack] step=7_wms_commit_OK container=%s is_active=%s status=%s "
        "fleet_registered=%s location_id=%s",
        c_code,
        bool(cart.is_active),
        cart.status,
        bool(cart.fleet_registered),
        cart.location_id,
    )

    try:
        dispatch_service.try_resolve_waiting_slot_queue(db)
        dispatch_service.try_resolve_waiting_cart_queue(db)
    except Exception as exc:
        logger.warning(
            "[remove_rack] step=8_queue_scan_WARN container=%s error=%s",
            c_code,
            exc,
        )

    publish_event(
        "floor.changed",
        {
            "reason": "rack_removed",
            "location_ids": loc_ids,
            "container_code": c_code,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    if called_fleet_out:
        msg = (
            f"Đã xóa Rack '{c_code}' khỏi vị trí '{loc_display}' và đồng bộ containerOut "
            f"trên KUKA Fleet thành công."
        )
    elif skipped_fleet_absent:
        msg = (
            f"Đã thu hồi Rack '{c_code}' khỏi WMS thành công "
            f"(containerQuery không thấy container trên KUKA Fleet)."
        )
    else:
        msg = f"Đã thu hồi Rack '{c_code}' khỏi WMS thành công."

    logger.info(
        "[remove_rack] step=9_done container=%s path=%s message=%s",
        c_code,
        (
            "query_hit_then_out"
            if called_fleet_out
            else ("query_empty_skip_out" if skipped_fleet_absent else "other")
        ),
        msg,
    )

    return {
        "success": True,
        "message": msg,
        "rack": serialize_rack(cart),
    }
