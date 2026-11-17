from typing import List, Optional

from sqlalchemy.orm import Session

from app.application.warehouse.ports.repositories.item_repository import IItemRepository
from app.domain.warehouse.entities.item import Item
from app.infrastructure.persistence.sqlalchemy.models.warehouse_orm import Item as ItemORM


def _to_domain(orm: ItemORM) -> Item:
    return Item(
        id=orm.id,
        sku=orm.sku,
        name=orm.name,
        warehouse_id=orm.warehouse_id,
        description=orm.description,
        standard_quantity_per_cart=orm.standard_quantity_per_cart or 120,
        details=orm.details or {},
    )


class ItemRepositoryImpl(IItemRepository):
    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, item_id: int) -> Optional[Item]:
        orm = self._session.query(ItemORM).filter(ItemORM.id == item_id).first()
        return _to_domain(orm) if orm else None

    def list_all(self) -> List[Item]:
        rows = self._session.query(ItemORM).order_by(ItemORM.id.asc()).all()
        return [_to_domain(r) for r in rows]

    def save(self, item: Item) -> Item:
        if item.id:
            orm = self._session.query(ItemORM).filter(ItemORM.id == item.id).first()
            if not orm:
                raise ValueError(f"Item id={item.id} not found")
            orm.sku = item.sku
            orm.name = item.name
            orm.description = item.description
            orm.standard_quantity_per_cart = item.standard_quantity_per_cart
            orm.details = item.details or {}
        else:
            orm = ItemORM(
                sku=item.sku,
                name=item.name,
                description=item.description,
                warehouse_id=item.warehouse_id,
                standard_quantity_per_cart=item.standard_quantity_per_cart,
                details=item.details or {},
            )
            self._session.add(orm)
        self._session.flush()
        return _to_domain(orm)
