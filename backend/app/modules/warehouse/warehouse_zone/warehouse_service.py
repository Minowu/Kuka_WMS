"""Warehouse service."""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse
from app.modules.warehouse.warehouse_zone.warehouse_schema import (
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseUpdate,
)


def _ensure_warehouse_exists(db: Session, warehouse_id: int) -> Warehouse:
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise ValueError(f"Warehouse id not found: {warehouse_id}")
    return warehouse


def list_warehouses(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> WarehouseListResponse:
    query = db.query(Warehouse)
    total = query.count()
    items = (
        query.order_by(Warehouse.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return WarehouseListResponse(
        items=[WarehouseResponse.model_validate(w) for w in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_warehouse_by_id(db: Session, warehouse_id: int) -> Optional[Warehouse]:
    return db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()


def create_warehouse(db: Session, body: WarehouseCreate) -> Warehouse:
    if db.query(Warehouse).filter(Warehouse.code == body.code).first():
        raise ValueError("Warehouse code already exists")
    warehouse = Warehouse(
        code=body.code.strip(),
        name=body.name or body.code.strip(),
        description=body.description,
    )
    try:
        db.add(warehouse)
        db.commit()
        db.refresh(warehouse)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return warehouse


def update_warehouse(
    db: Session, warehouse_id: int, body: WarehouseUpdate
) -> Optional[Warehouse]:
    warehouse = get_warehouse_by_id(db, warehouse_id)
    if not warehouse:
        return None
    data = body.model_dump(exclude_unset=True)
    if "code" in data and data["code"]:
        existing = (
            db.query(Warehouse)
            .filter(
                Warehouse.code == data["code"],
                Warehouse.id != warehouse_id,
            )
            .first()
        )
        if existing:
            raise ValueError("Warehouse code already exists")
        warehouse.code = data["code"].strip()
    if "name" in data and data["name"] is not None:
        warehouse.name = data["name"]
    if "description" in data:
        warehouse.description = data["description"]
    try:
        db.commit()
        db.refresh(warehouse)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return warehouse


def delete_warehouse(db: Session, warehouse_id: int) -> bool:
    warehouse = get_warehouse_by_id(db, warehouse_id)
    if not warehouse:
        return False
    if (
        db.query(Location)
        .filter(
            Location.warehouse_id == warehouse_id,
            Location.is_active.is_(True),
        )
        .first()
    ):
        raise ValueError("Cannot delete warehouse: locations still exist")

    from app.modules.warehouse.item.item_model import Item
    from app.modules.warehouse.location_map.location_model import WarehouseMap
    from app.modules.warehouse.notificcation.notification_model import Notification

    has_Dependencies = (
        db.query(Location).filter(Location.warehouse_id == warehouse_id).first()
        or db.query(Item).filter(Item.warehouse_id == warehouse_id).first()
        or db.query(WarehouseMap).filter(WarehouseMap.warehouse_id == warehouse_id).first()
        or db.query(Notification).filter(Notification.warehouse_id == warehouse_id).first()
    )
    if has_Dependencies:
        raise ValueError("Cannot delete warehouse: related records still exist")

    try:
        db.delete(warehouse)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Cannot delete warehouse: related records still exist") from e
    return True
