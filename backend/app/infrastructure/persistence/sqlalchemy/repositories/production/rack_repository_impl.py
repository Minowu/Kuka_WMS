"""Rack repository — maps ItemStock containers to Rack domain entity."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.application.production.ports.repositories.rack_repository import IRackRepository
from app.domain.production.entities.rack import Rack
from app.infrastructure.persistence.sqlalchemy.mappers.production_mapper import (
    apply_rack_to_orm,
    rack_to_domain,
)
from app.infrastructure.persistence.sqlalchemy.models.warehouse_orm import ItemStock


class RackRepositoryImpl(IRackRepository):
    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, rack_id: int) -> Optional[Rack]:
        orm = self._session.query(ItemStock).filter(ItemStock.id == rack_id).first()
        return rack_to_domain(orm) if orm else None

    def get_by_code(self, container_code: str) -> Optional[Rack]:
        code = (container_code or "").strip()
        orm = self._session.query(ItemStock).filter(ItemStock.container_code == code).first()
        return rack_to_domain(orm) if orm else None

    def list_active(self, include_inactive: bool = False) -> List[Rack]:
        q = self._session.query(ItemStock).filter(ItemStock.container_code.isnot(None))
        if not include_inactive:
            q = q.filter(ItemStock.is_active.is_(True))
        return [rack_to_domain(r) for r in q.order_by(ItemStock.id.asc()).all()]

    def save(self, rack: Rack) -> Rack:
        if rack.id:
            orm = self._session.query(ItemStock).filter(ItemStock.id == rack.id).first()
            if not orm:
                raise ValueError(f"Rack id={rack.id} not found")
            apply_rack_to_orm(rack, orm)
        else:
            orm = ItemStock(
                container_code=rack.container_code,
                item_id=rack.item_id,
                location_id=rack.location_id,
                quantity=rack.quantity,
                current_stage_level=rack.current_stage_level,
                status=rack.status,
                is_active=rack.is_active,
                is_locked=rack.is_locked,
                locked_by_mission_code=rack.locked_by_mission_code,
                destination_location_id=rack.destination_location_id,
            )
            self._session.add(orm)
        self._session.flush()
        return rack_to_domain(orm)
