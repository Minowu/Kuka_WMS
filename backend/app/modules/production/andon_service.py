"""Service layer for Production Andon TV displays."""

from typing import Optional
from sqlalchemy.orm import Session, joinedload

from app.core.logger import get_logger
from app.modules.production.andon_schema import (
    AndonRawMaterialDemand,
    AndonRawMaterialResponse,
    AndonRawSlotStatus,
)
from app.modules.production.production_models import TransportQueue, TransportRequest
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("production.andon")


def get_raw_material_andon_queue(
    db: Session,
    warehouse_id: Optional[int] = None,
) -> AndonRawMaterialResponse:
    """
    Bảng điều độ Andon hiển thị nhu cầu cấp phôi nguyên liệu trên màn hình TV xưởng:
    - Danh sách các yêu cầu phôi thô (target_stage_level = 0) đang chờ xếp hàng (TransportQueue.status == 'PENDING').
    - Trạng thái 7 ô cấp phôi tại bãi RAW_MATERIAL (ô trống vs ô có hàng).
    - Tự động biến mất khỏi danh sách khi xe phôi được nạp và gán cho máy CNC thành công.
    """
    # 1. Danh sách yêu cầu đang chờ phôi (Demands)
    queue_query = (
        db.query(TransportQueue, TransportRequest, Item, Location)
        .join(TransportRequest, TransportQueue.request_id == TransportRequest.id)
        .join(Item, TransportRequest.item_id == Item.id)
        .join(Location, TransportRequest.destination_location_id == Location.id)
        .outerjoin(Location.machine)
        .options(joinedload(Location.machine))
        .filter(
            TransportQueue.queue_type == "WAITING_CART",
            TransportQueue.status == "PENDING",
            TransportQueue.target_stage_level == 0,
        )
    )
    if warehouse_id:
        queue_query = queue_query.filter(Location.warehouse_id == warehouse_id)

    queue_entries = (
        queue_query.order_by(
            TransportQueue.priority.asc(),
            TransportQueue.created_at.asc(),
        ).all()
    )

    demands: list[AndonRawMaterialDemand] = []
    for queue_item, req, item, dest_loc in queue_entries:
        machine = dest_loc.machine
        machine_code = machine.machine_code if machine else (dest_loc.location_code or f"LOC-{dest_loc.id}")
        machine_name = machine.machine_name if machine else (dest_loc.location_name or machine_code)

        # Mốc thời gian bấm tĩnh theo giờ HH:MM:SS
        called_time_str = req.created_at.strftime("%H:%M:%S") if req.created_at else ""

        demands.append(
            AndonRawMaterialDemand(
                id=queue_item.id,
                request_code=req.request_code,
                model_code=item.sku or f"ITEM-{item.id}",
                model_name=item.name,
                machine_code=machine_code,
                machine_name=machine_name,
                position_index=dest_loc.position_index,
                destination_location_code=dest_loc.location_code,
                called_at=called_time_str,
                priority=queue_item.priority,
            )
        )

    # 2. Trạng thái các ô RAW_MATERIAL (RAW-01 đến RAW-07)
    slot_query = db.query(Location).filter(
        Location.location_type == "RAW_MATERIAL",
        Location.is_active == True,
    )
    if warehouse_id:
        slot_query = slot_query.filter(Location.warehouse_id == warehouse_id)

    locations = (
        slot_query.order_by(
            Location.position_index.asc().nullslast(),
            Location.location_code.asc(),
        ).all()
    )

    loc_ids = [loc.id for loc in locations]
    carts = (
        db.query(ItemStock)
        .options(joinedload(ItemStock.item))
        .filter(
            ItemStock.location_id.in_(loc_ids),
            ItemStock.is_active == True,
        )
        .all()
    )
    cart_by_loc_id = {c.location_id: c for c in carts}

    raw_slots: list[AndonRawSlotStatus] = []
    for loc in locations:
        cart = cart_by_loc_id.get(loc.id)
        has_cart = cart is not None
        cart_code = cart.container_code if cart else None
        model_code = (cart.item.sku if cart.item else None) if cart else None
        model_name = (cart.item.name if cart.item else None) if cart else None

        raw_slots.append(
            AndonRawSlotStatus(
                location_id=loc.id,
                location_code=loc.location_code,
                name=loc.location_name or loc.location_code,
                position_index=loc.position_index,
                has_cart=has_cart,
                cart_code=cart_code,
                model_code=model_code,
                model_name=model_name,
            )
        )

    return AndonRawMaterialResponse(
        demands=demands,
        raw_slots=raw_slots,
    )
