from typing import Optional

from sqlalchemy.orm import Session

from app.application.fleet.ports.fleet_task_repository import IFleetTaskRepository
from app.domain.fleet.entities.fleet_task import FleetTask
from app.infrastructure.persistence.sqlalchemy.models.fleet_orm import FleetTask as FleetTaskORM


def _to_domain(orm: FleetTaskORM) -> FleetTask:
    return FleetTask(
        id=orm.id,
        mission_code=orm.mission_code,
        transport_request_id=orm.transport_request_id,
        status=orm.status,
        pickup_location_id=orm.pickup_location_id,
        dropoff_location_id=orm.dropoff_location_id,
        container_id=orm.container_id,
        container_code=orm.container_code,
        fleet_request_id=orm.fleet_request_id,
        robot_id=orm.robot_id,
        error_message=orm.error_message,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class FleetTaskRepositoryImpl(IFleetTaskRepository):
    def __init__(self, session: Session):
        self._session = session

    def get_by_mission_code(self, mission_code: str) -> Optional[FleetTask]:
        orm = (
            self._session.query(FleetTaskORM)
            .filter(FleetTaskORM.mission_code == mission_code)
            .first()
        )
        return _to_domain(orm) if orm else None

    def save(self, task: FleetTask) -> FleetTask:
        if task.id:
            orm = self._session.query(FleetTaskORM).filter(FleetTaskORM.id == task.id).first()
            if not orm:
                raise ValueError(f"FleetTask id={task.id} not found")
            orm.status = task.status
            orm.error_message = task.error_message
            orm.robot_id = task.robot_id
        else:
            orm = FleetTaskORM(
                mission_code=task.mission_code,
                transport_request_id=task.transport_request_id,
                status=task.status,
                pickup_location_id=task.pickup_location_id,
                dropoff_location_id=task.dropoff_location_id,
                container_id=task.container_id,
                container_code=task.container_code,
                fleet_request_id=task.fleet_request_id,
                robot_id=task.robot_id,
                error_message=task.error_message,
            )
            self._session.add(orm)
        self._session.flush()
        return _to_domain(orm)
