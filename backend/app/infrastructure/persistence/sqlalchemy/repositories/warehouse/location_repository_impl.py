from typing import List, Optional

from sqlalchemy.orm import Session

from app.application.warehouse.ports.repositories.location_repository import ILocationRepository
from app.domain.warehouse.entities.location import Location
from app.infrastructure.persistence.sqlalchemy.models.warehouse_orm import Location as LocationORM


def _to_domain(orm: LocationORM) -> Location:
    return Location(
        id=orm.id,
        location_code=orm.location_code,
        location_name=orm.location_name or orm.location_code,
        warehouse_id=orm.warehouse_id,
        location_type=orm.location_type or "UNASSIGNED",
        location_label=orm.location_label,
        machine_id=orm.machine_id,
        position_index=orm.position_index,
        is_active=bool(orm.is_active),
    )


class LocationRepositoryImpl(ILocationRepository):
    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, location_id: int) -> Optional[Location]:
        orm = self._session.query(LocationORM).filter(LocationORM.id == location_id).first()
        return _to_domain(orm) if orm else None

    def list_by_warehouse(self, warehouse_id: int, active_only: bool = True) -> List[Location]:
        q = self._session.query(LocationORM).filter(LocationORM.warehouse_id == warehouse_id)
        if active_only:
            q = q.filter(LocationORM.is_active.is_(True))
        return [_to_domain(r) for r in q.order_by(LocationORM.id.asc()).all()]
