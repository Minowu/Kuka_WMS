"""Machine repository implementation (SQLAlchemy)."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.application.production.ports.repositories.machine_repository import IMachineRepository
from app.domain.production.entities.machine import Machine
from app.infrastructure.persistence.sqlalchemy.mappers.production_mapper import (
    machine_to_domain,
    machine_to_orm,
)
from app.infrastructure.persistence.sqlalchemy.models.production_orm import Machine as MachineORM


class MachineRepositoryImpl(IMachineRepository):
    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, machine_id: int) -> Optional[Machine]:
        orm = self._session.query(MachineORM).filter(MachineORM.id == machine_id).first()
        return machine_to_domain(orm) if orm else None

    def get_by_code(self, machine_code: str) -> Optional[Machine]:
        orm = (
            self._session.query(MachineORM)
            .filter(MachineORM.machine_code == machine_code)
            .first()
        )
        return machine_to_domain(orm) if orm else None

    def list_by_warehouse(self, warehouse_id: int) -> List[Machine]:
        rows = (
            self._session.query(MachineORM)
            .filter(MachineORM.warehouse_id == warehouse_id)
            .order_by(MachineORM.machine_code.asc())
            .all()
        )
        return [machine_to_domain(r) for r in rows]

    def save(self, machine: Machine) -> Machine:
        if machine.id:
            orm = self._session.query(MachineORM).filter(MachineORM.id == machine.id).first()
            if not orm:
                raise ValueError(f"Machine id={machine.id} not found")
            machine_to_orm(machine, orm)
        else:
            orm = machine_to_orm(machine)
            self._session.add(orm)
        self._session.flush()
        return machine_to_domain(orm)
