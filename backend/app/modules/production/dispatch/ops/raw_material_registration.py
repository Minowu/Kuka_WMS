"""Auto-split from dispatch_core — keep behavior identical."""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from sqlalchemy.orm import Session

from app.core.logger import bind_context, get_logger, log_context
from app.modules.production.production_models import (
    FleetTask,
    Machine,
    ProductionRecord,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportQueue,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("wms.dispatch")


def register_rack_at_raw_material_impl(
    core,
    db: Session,
    location_id: int,
    item_id: int,
    container_code: str,
    quantity: Optional[int] = None,
    lot_number: Optional[str] = None,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """Register rack QR at Raw Material location and auto-dispatch waiting CNC requests."""
    clean_container_code = container_code.strip()
    if not clean_container_code:
        raise ValueError("Mã QR của rack (container_code) không được để trống.")

    location = db.query(Location).filter(Location.id == location_id, Location.is_active.is_(True)).first()
    if not location:
        raise ValueError(f"Vị trí cấp phôi (ID={location_id}) không tồn tại hoặc đã bị khóa.")
    if location.location_type != "RAW_MATERIAL":
        raise ValueError(f"Vị trí '{location.location_code}' không phải là vị trí Khu Nguyên Liệu (RAW_MATERIAL).")

    bind_context(
        container_code=clean_container_code,
        station_code=location.location_code,
    )

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError(f"Model sản phẩm ID={item_id} không tồn tại hoặc đã ngừng hoạt động.")

    occupying_cart = (
        db.query(ItemStock)
        .filter(
            ItemStock.location_id == location.id,
            ItemStock.is_active.is_(True),
            ItemStock.container_code != clean_container_code,
        )
        .first()
    )
    if occupying_cart:
        raise ValueError(f"Vị trí '{location.location_code}' đang có xe/rack '{occupying_cart.container_code}' đỗ.")

    qty = quantity if (quantity is not None and quantity > 0) else (item.standard_quantity_per_cart or 120)

    cart = db.query(ItemStock).filter(ItemStock.container_code == clean_container_code).first()
    now = datetime.now(timezone.utc)
    if cart:
        if cart.is_locked:
            raise ValueError(f"Rack '{clean_container_code}' đang bị khóa bởi tác vụ vận chuyển '{cart.locked_by_mission_code}'.")
        if cart.is_active and cart.location_id and cart.location_id != location.id:
            curr_loc = db.query(Location).filter(Location.id == cart.location_id).first()
            loc_name = curr_loc.location_code if curr_loc else f"ID={cart.location_id}"
            raise ValueError(
                f"Rack '{clean_container_code}' hiện đang hoạt động tại vị trí '{loc_name}'. "
                f"Cần hoàn thành chu trình trước khi đăng ký lại ở Phôi Thô."
            )
        cart.item_id = item.id
        cart.location_id = location.id
        cart.destination_location_id = None
        cart.quantity = qty
        cart.current_stage_level = 0
        cart.status = "available"
        cart.is_active = True
        cart.is_locked = False
        cart.locked_by_mission_code = None
        cart.fleet_registered = True
        cart.created_at = now
    else:
        cart = ItemStock(
            container_code=clean_container_code,
            item_id=item.id,
            location_id=location.id,
            quantity=qty,
            current_stage_level=0,
            status="available",
            is_active=True,
            is_locked=False,
            fleet_registered=True,
            created_at=now,
        )
        db.add(cart)

    # Gọi KUKA Fleet để khai báo containerIn tại vị trí
    # Nếu Fleet từ chối, exception IcsError sẽ được ném ra -> rollback toàn bộ thay đổi DB
    try:
        core.fleet_client.fleet_insert_rack(location.location_code, clean_container_code)
    except Exception as e:
        db.rollback()
        logger.error(
            "Khai báo xe phôi '%s' vào vị trí '%s' thất bại trên KUKA Fleet: %s",
            clean_container_code,
            location.location_code,
            e,
            exc_info=True,
        )
        raise ValueError(f"KUKA Fleet từ chối tiếp nhận xe phôi: {e}") from e

    db.flush()

    resolved = core.queue_service.try_resolve_waiting_cart_queue(
        db,
        stage_level=0,
        lock_and_dispatch_fn=core.lock_cart_and_dispatch_fleet_task,
    )
    loc_ids = sorted({int(lid) for lid in (location.id, cart.destination_location_id) if lid is not None})
    recipient_user_ids = resolve_location_recipient_user_ids(
        db,
        loc_ids,
        extra_user_ids=[operator_id],
    )
    db.commit()
    db.refresh(cart)

    publish_event(
        "floor.changed",
        {
            "reason": "rack_registered",
            "location_ids": loc_ids,
            "container_code": clean_container_code,
        },
        user_ids=recipient_user_ids,
        admins=True,
    )

    return {
        "success": True,
        "container_id": cart.id,
        "container_code": clean_container_code,
        "item_id": item.id,
        "item_name": item.name,
        "sku": item.sku,
        "location_id": location.id,
        "location_code": location.location_code,
        "quantity": qty,
        "current_stage_level": 0,
        "is_locked": cart.is_locked,
        "fleet_inserted": True,
        "resolved_queue_count": resolved,
        "dispatched_mission_code": cart.locked_by_mission_code,
    }


def register_rack_at_raw_material(
    core,
    db: Session,
    location_id: int,
    item_id: int,
    container_code: str,
    quantity: Optional[int] = None,
    lot_number: Optional[str] = None,
    operator_id: Optional[int] = None,
) -> dict[str, Any]:
    """Facade → RegisterRackUseCase."""
    from app.application.production.use_cases.rack_management.register_rack import (
        RegisterRackRequest,
    )
    from app.infrastructure.di.production_factory import build_register_rack_use_case

    return build_register_rack_use_case(db, core=core).execute(
        RegisterRackRequest(
            location_id=location_id,
            item_id=item_id,
            container_code=container_code,
            quantity=quantity,
            lot_number=lot_number,
            operator_id=operator_id,
        )
    )
