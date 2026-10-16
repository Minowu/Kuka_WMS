"""Item stock service."""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import (
    ItemStock,
    countable_stock_level_criterion,
    positive_stock_quantity_criterion,
)
from app.modules.warehouse.item_stock.item_stock_schema import (
    ItemStockCreate,
    ItemStockListResponse,
    ItemStockResponse,
    ItemStockSplitListResponse,
    ItemStockUpdate,
)
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Zone


def _stock_query(db: Session, *, include_inactive: bool = False):
    q = db.query(ItemStock)
    if not include_inactive:
        q = q.filter(ItemStock.is_active.is_(True))
    return q


def _ensure_item_and_location(db: Session, item_id: int, location_id: int) -> Item:
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.is_active.is_(True))
        .first()
    )
    if not item:
        raise ValueError(f"Item id not found: {item_id}")
    location = (
        db.query(Location)
        .filter(Location.id == location_id, Location.is_active.is_(True))
        .first()
    )
    if not location:
        raise ValueError(f"Location id not found: {location_id}")
    return item




def list_item_stocks(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    item_id: Optional[int] = None,
    location_id: Optional[int] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> ItemStockListResponse:
    if is_active is None:
        query = _stock_query(db, include_inactive=False)
    else:
        query = db.query(ItemStock).filter(ItemStock.is_active.is_(is_active))
    if item_id is not None:
        query = query.filter(ItemStock.item_id == item_id)
    if location_id is not None:
        query = query.filter(ItemStock.location_id == location_id)
    if status is not None:
        query = query.filter(ItemStock.status == status)
    total = query.count()
    items = (
        query.order_by(ItemStock.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ItemStockListResponse(
        items=[ItemStockResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_item_stock_by_id(
    db: Session, stock_id: int, *, include_inactive: bool = False
) -> Optional[ItemStock]:
    return (
        _stock_query(db, include_inactive=include_inactive)
        .filter(ItemStock.id == stock_id)
        .first()
    )


def create_item_stock(db: Session, body: ItemStockCreate) -> ItemStock:
    item = _ensure_item_and_location(db, body.item_id, body.location_id)
    if body.quantity < 0:
        raise ValueError("Quantity must be >= 0")
    stock = ItemStock(
        item_id=body.item_id,
        location_id=body.location_id,
        quantity=body.quantity,
        status=body.status,
        is_active=True,
    )
    try:
        db.add(stock)
        db.commit()
        db.refresh(stock)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return stock


def update_item_stock(
    db: Session, stock_id: int, body: ItemStockUpdate
) -> Optional[ItemStock]:
    stock = get_item_stock_by_id(db, stock_id, include_inactive=True)
    if not stock:
        return None
    data = body.model_dump(exclude_unset=True)
    item_id = data.get("item_id", stock.item_id)
    location_id = data.get("location_id", stock.location_id)
    if "item_id" in data or "location_id" in data:
        _ensure_item_and_location(db, item_id, location_id)
        stock.item_id = item_id
        stock.location_id = location_id
    if "quantity" in data:
        if data["quantity"] is not None and data["quantity"] < 0:
            raise ValueError("Quantity must be >= 0")
        stock.quantity = data["quantity"]
    for field in ("status", "is_active"):
        if field in data:
            setattr(stock, field, data[field])
    try:
        db.commit()
        db.refresh(stock)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return stock


def delete_item_stock(db: Session, stock_id: int) -> bool:
    stock = get_item_stock_by_id(db, stock_id)
    if not stock:
        return False
    if stock.is_locked:
        raise ValueError("Cannot delete item stock: cart is currently locked in an active transport task")
    stock.is_active = False
    db.commit()
    return True

def get_stock_split(db: Session, item_id: int) -> ItemStockSplitListResponse:
    stocks = (
        _stock_query(db)
        .join(Location, Location.id == ItemStock.location_id)
        .join(Zone, Zone.id == Location.zone_id)
        .filter(
            ItemStock.item_id == item_id,
            ItemStock.status == "split",
            Zone.code.in_(settings.zone_storage),
            ItemStock.available_quantity > 0,
            positive_stock_quantity_criterion(),
            countable_stock_level_criterion(),
        )
        .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
        .all()
    )
    return ItemStockSplitListResponse(
        items=[ItemStockResponse.model_validate(s) for s in stocks],
        total=len(stocks),
    )
