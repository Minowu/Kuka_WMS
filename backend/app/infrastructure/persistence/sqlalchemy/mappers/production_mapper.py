"""Map SQLAlchemy ORM ↔ Production domain entities."""

from typing import Optional

from app.domain.production.entities.machine import Machine as MachineEntity
from app.domain.production.entities.rack import Rack as RackEntity
from app.domain.production.entities.transport_request import (
    TransportRequest as TransportRequestEntity,
)
from app.infrastructure.persistence.sqlalchemy.models.production_orm import Machine as MachineORM
from app.infrastructure.persistence.sqlalchemy.models.production_orm import (
    TransportRequest as TransportRequestORM,
)
from app.infrastructure.persistence.sqlalchemy.models.warehouse_orm import ItemStock as ItemStockORM


def machine_to_domain(orm: MachineORM) -> MachineEntity:
    return MachineEntity(
        id=orm.id,
        machine_code=orm.machine_code,
        machine_name=orm.machine_name,
        warehouse_id=orm.warehouse_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def machine_to_orm(entity: MachineEntity, orm: Optional[MachineORM] = None) -> MachineORM:
    target = orm or MachineORM()
    target.machine_code = entity.machine_code
    target.machine_name = entity.machine_name
    target.warehouse_id = entity.warehouse_id
    return target


def transport_request_to_domain(orm: TransportRequestORM) -> TransportRequestEntity:
    return TransportRequestEntity(
        id=orm.id,
        request_code=orm.request_code,
        request_type=orm.request_type,
        item_id=orm.item_id,
        destination_location_id=orm.destination_location_id,
        required_stage_level=orm.required_stage_level or 0,
        status=orm.status,
        priority=orm.priority or 10,
        source_location_id=orm.source_location_id,
        container_id=orm.container_id,
        created_by=orm.created_by,
        created_at=orm.created_at,
    )


def transport_request_to_orm(
    entity: TransportRequestEntity,
    orm: Optional[TransportRequestORM] = None,
) -> TransportRequestORM:
    target = orm or TransportRequestORM()
    target.request_code = entity.request_code
    target.request_type = entity.request_type
    target.item_id = entity.item_id
    target.destination_location_id = entity.destination_location_id
    target.required_stage_level = entity.required_stage_level
    target.status = entity.status
    target.priority = entity.priority
    target.source_location_id = entity.source_location_id
    target.container_id = entity.container_id
    target.created_by = entity.created_by
    return target


def rack_to_domain(orm: ItemStockORM) -> RackEntity:
    return RackEntity(
        id=orm.id,
        container_code=orm.container_code or "",
        item_id=orm.item_id,
        location_id=orm.location_id,
        quantity=int(orm.quantity or 0),
        current_stage_level=orm.current_stage_level or 0,
        status=orm.status or "available",
        is_active=bool(orm.is_active),
        is_locked=bool(orm.is_locked),
        locked_by_mission_code=orm.locked_by_mission_code,
        destination_location_id=orm.destination_location_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def apply_rack_to_orm(entity: RackEntity, orm: ItemStockORM) -> ItemStockORM:
    orm.container_code = entity.container_code
    orm.item_id = entity.item_id
    orm.location_id = entity.location_id
    orm.quantity = entity.quantity
    orm.current_stage_level = entity.current_stage_level
    orm.status = entity.status
    orm.is_active = entity.is_active
    orm.is_locked = entity.is_locked
    orm.locked_by_mission_code = entity.locked_by_mission_code
    orm.destination_location_id = entity.destination_location_id
    return orm
