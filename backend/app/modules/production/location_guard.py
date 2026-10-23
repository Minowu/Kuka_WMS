"""Guard dùng chung cho Station/Machine: tìm node bản đồ & chặn thao tác khi vị trí đang có hàng."""

from typing import Optional

from sqlalchemy.orm import Session

from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse


def resolve_warehouse_id(db: Session, warehouse_id: Optional[int] = None) -> int:
    if warehouse_id:
        return warehouse_id
    wh = db.query(Warehouse).first()
    if not wh:
        raise ValueError("Hệ thống chưa khởi tạo dữ liệu Nhà kho (Warehouse). Vui lòng tạo kho trước.")
    return wh.id


def find_map_node(
    db: Session,
    warehouse_id: int,
    node_ref: Optional[str] = None,
    location_code: Optional[str] = None,
) -> Optional[Location]:
    """Tìm node theo location_code (UUID) / location_label ('216') / location_name."""
    node_ref = (node_ref or "").strip()
    if node_ref:
        loc = (
            db.query(Location)
            .filter(
                Location.warehouse_id == warehouse_id,
                (Location.location_code == node_ref)
                | (Location.location_label == node_ref)
                | (Location.location_name == node_ref),
            )
            .first()
        )
        if loc:
            return loc
    code = (location_code or "").strip()
    if code:
        return (
            db.query(Location)
            .filter(Location.warehouse_id == warehouse_id, Location.location_code == code)
            .first()
        )
    return None


def _describe(loc: Location) -> str:
    return loc.location_name or loc.location_label or loc.location_code


def ensure_location_has_no_stock(db: Session, loc: Location, action: str) -> None:
    """Raise nếu tại vị trí đang có xe/phôi (item_stock active) hoặc có AGV đang chở hàng tới (đã lock)."""
    stock = (
        db.query(ItemStock)
        .filter(ItemStock.location_id == loc.id, ItemStock.is_active.is_(True))
        .first()
    )
    if stock:
        label = stock.container_code or (stock.item.sku if stock.item else f"stock #{stock.id}")
        raise ValueError(
            f"Không thể {action}: vị trí '{_describe(loc)}' đang có xe/phôi ({label}, SL: {stock.quantity}). "
            "Vui lòng dọn hoặc chuyển hàng đi trước."
        )

    incoming = (
        db.query(ItemStock)
        .filter(
            ItemStock.destination_location_id == loc.id,
            ItemStock.is_locked.is_(True),
            ItemStock.is_active.is_(True),
        )
        .first()
    )
    if incoming:
        raise ValueError(
            f"Không thể {action}: vị trí '{_describe(loc)}' đang được giữ chỗ cho nhiệm vụ AGV "
            f"{incoming.locked_by_mission_code or ''} đang chở hàng tới."
        )


def release_location(loc: Location, db: Optional[Session] = None) -> None:
    """Trả node về trạng thái tự do (không xóa bản ghi vì đây là node vật lý của bản đồ)."""
    if db is not None:
        from app.modules.production.production_models import UserLocation
        db.query(UserLocation).filter(UserLocation.location_id == loc.id).delete(synchronize_session=False)
    loc.location_type = "UNASSIGNED"
    loc.location_name = loc.location_label or loc.location_code or str(loc.id)
    loc.machine_id = None
    loc.position_index = None
    loc.is_active = True
