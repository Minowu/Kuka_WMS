"""Unit and ItemUnit service."""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.unit.unit_model import ItemUnit, Unit
from app.modules.warehouse.unit.unit_schema import (
    ConvertQuantityRequest,
    ConvertQuantityResponse,
    ItemAvailableUnitsResponse,
    ItemAvailableUnitOption,
    ItemUnitCreate,
    ItemUnitListResponse,
    ItemUnitResponse,
    ItemUnitUpdate,
    UnitCreate,
    UnitListResponse,
    UnitResponse,
    UnitUpdate,
)


# --- Unit ---

def list_units(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
) -> UnitListResponse:
    query = db.query(Unit)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Unit.name.ilike(like))
    total = query.count()
    items = (
        query.order_by(Unit.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return UnitListResponse(
        items=[UnitResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_unit_by_id(db: Session, unit_id: int) -> Optional[Unit]:
    return db.query(Unit).filter(Unit.id == unit_id).first()


def create_unit(db: Session, body: UnitCreate) -> Unit:
    name = body.name.strip()
    if db.query(Unit).filter(Unit.name == name).first():
        raise ValueError("Unit name already exists")
    unit = Unit(name=name, description=body.description)
    try:
        db.add(unit)
        db.commit()
        db.refresh(unit)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return unit


def update_unit(db: Session, unit_id: int, body: UnitUpdate) -> Optional[Unit]:
    unit = get_unit_by_id(db, unit_id)
    if not unit:
        return None
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        name = data["name"].strip()
        existing = (
            db.query(Unit)
            .filter(Unit.name == name, Unit.id != unit_id)
            .first()
        )
        if existing:
            raise ValueError("Unit name already exists")
        unit.name = name
    if "description" in data:
        unit.description = data["description"]
    try:
        db.commit()
        db.refresh(unit)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return unit


def delete_unit(db: Session, unit_id: int) -> bool:
    unit = get_unit_by_id(db, unit_id)
    if not unit:
        return False
    if db.query(ItemUnit).filter(ItemUnit.unit_id == unit_id).first():
        raise ValueError("Cannot delete unit: item units still exist")
    try:
        db.delete(unit)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return True


# --- ItemUnit ---

def _ensure_item_exists(db: Session, item_id: int) -> None:
    if not (
        db.query(Item)
        .filter(Item.id == item_id, Item.is_active.is_(True))
        .first()
    ):
        raise ValueError(f"Item id not found: {item_id}")


def _ensure_unit_exists(db: Session, unit_id: int) -> None:
    if not db.query(Unit).filter(Unit.id == unit_id).first():
        raise ValueError(f"Unit id not found: {unit_id}")


def item_unit_to_response(item_unit: ItemUnit) -> ItemUnitResponse:
    return ItemUnitResponse(
        id=item_unit.id,
        item_id=item_unit.item_id,
        unit_id=item_unit.unit_id,
        conversion_factor=item_unit.conversion_factor,
        item_name=item_unit.item.name if item_unit.item else None,
        item_sku=item_unit.item.sku if item_unit.item else None,
        unit_name=item_unit.unit.name if item_unit.unit else None,
        created_at=item_unit.created_at,
        updated_at=item_unit.updated_at,
    )


def _ensure_item_unit_unique(
    db: Session,
    *,
    item_id: int,
    unit_id: int,
    exclude_id: Optional[int] = None,
) -> None:
    query = db.query(ItemUnit).filter(
        ItemUnit.item_id == item_id,
        ItemUnit.unit_id == unit_id,
    )
    if exclude_id is not None:
        query = query.filter(ItemUnit.id != exclude_id)
    if query.first():
        raise ValueError("Item unit mapping already exists for this item and unit")


def list_item_units(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    item_id: Optional[int] = None,
    unit_id: Optional[int] = None,
) -> ItemUnitListResponse:
    query = db.query(ItemUnit).options(
        joinedload(ItemUnit.item),
        joinedload(ItemUnit.unit),
    )
    if item_id is not None:
        query = query.filter(ItemUnit.item_id == item_id)
    if unit_id is not None:
        query = query.filter(ItemUnit.unit_id == unit_id)
    total = query.count()
    items = (
        query.order_by(ItemUnit.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ItemUnitListResponse(
        items=[item_unit_to_response(iu) for iu in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_item_unit_by_id(db: Session, item_unit_id: int) -> Optional[ItemUnit]:
    return (
        db.query(ItemUnit)
        .options(
            joinedload(ItemUnit.item),
            joinedload(ItemUnit.unit),
        )
        .filter(ItemUnit.id == item_unit_id)
        .first()
    )


def create_item_unit(db: Session, body: ItemUnitCreate) -> ItemUnit:
    _ensure_item_exists(db, body.item_id)
    _ensure_unit_exists(db, body.unit_id)
    _ensure_item_unit_unique(db, item_id=body.item_id, unit_id=body.unit_id)
    item_unit = ItemUnit(
        item_id=body.item_id,
        unit_id=body.unit_id,
        conversion_factor=body.conversion_factor,
    )
    try:
        db.add(item_unit)
        db.commit()
        db.refresh(item_unit)
        item_unit = get_item_unit_by_id(db, item_unit.id)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return item_unit


def update_item_unit(
    db: Session, item_unit_id: int, body: ItemUnitUpdate
) -> Optional[ItemUnit]:
    item_unit = get_item_unit_by_id(db, item_unit_id)
    if not item_unit:
        return None
    data = body.model_dump(exclude_unset=True)
    item_id = data.get("item_id", item_unit.item_id)
    unit_id = data.get("unit_id", item_unit.unit_id)
    if "item_id" in data or "unit_id" in data:
        _ensure_item_exists(db, item_id)
        _ensure_unit_exists(db, unit_id)
        _ensure_item_unit_unique(
            db,
            item_id=item_id,
            unit_id=unit_id,
            exclude_id=item_unit_id,
        )
        item_unit.item_id = item_id
        item_unit.unit_id = unit_id
    if "conversion_factor" in data:
        item_unit.conversion_factor = data["conversion_factor"]
    try:
        db.commit()
        db.refresh(item_unit)
        item_unit = get_item_unit_by_id(db, item_unit.id)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return item_unit


def delete_item_unit(db: Session, item_unit_id: int) -> bool:
    item_unit = get_item_unit_by_id(db, item_unit_id)
    if not item_unit:
        return False
    try:
        db.delete(item_unit)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return True


def convert_quantity(
    db: Session, item_id: int, unit_id: int, quantity: int
) -> ConvertQuantityResponse:
    item = (
        db.query(Item)
        .options(joinedload(Item.unit))
        .filter(Item.id == item_id, Item.is_active.is_(True))
        .first()
    )
    if not item:
        raise ValueError("Item not found")
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")

    if unit_id == item.base_unit_id:
        converted = quantity
    else:
        item_unit = (
            db.query(ItemUnit)
            .filter(ItemUnit.item_id == item_id, ItemUnit.unit_id == unit_id)
            .first()
        )
        if not item_unit:
            raise ValueError("Item unit not found")
        converted = quantity * item_unit.conversion_factor

    return ConvertQuantityResponse(
        converted_quantity=converted,
        base_unit_id=item.base_unit_id,
        base_unit_name=item.unit.name if item.unit else "",
    )


def get_item_unit_by_item(db: Session, item_id: int) -> ItemAvailableUnitsResponse:
    item = (
        db.query(Item)
        .options(joinedload(Item.unit))
        .filter(Item.id == item_id, Item.is_active.is_(True))
        .first()
    )
    if not item:
        raise ValueError("Item not found")

    item_units = (
        db.query(ItemUnit)
        .options(joinedload(ItemUnit.unit))
        .filter(ItemUnit.item_id == item_id)
        .order_by(ItemUnit.id)
        .all()
    )

    units: list[ItemAvailableUnitOption] = [
        ItemAvailableUnitOption(
            unit_id=item.base_unit_id,
            unit_name=item.unit.name if item.unit else "",
            is_base_unit=True,
        )
    ]
    seen = {item.base_unit_id}
    for item_unit in item_units:
        if item_unit.unit_id in seen:
            continue
        units.append(
            ItemAvailableUnitOption(
                unit_id=item_unit.unit_id,
                unit_name=item_unit.unit.name if item_unit.unit else "",
                conversion_factor=item_unit.conversion_factor,
                is_base_unit=False,
            )
        )
        seen.add(item_unit.unit_id)

    return ItemAvailableUnitsResponse(
        item_id=item_id,
        base_unit_id=item.base_unit_id,
        base_unit_name=item.unit.name if item.unit else "",
        units=units,
    )