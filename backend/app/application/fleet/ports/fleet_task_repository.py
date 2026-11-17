from abc import ABC, abstractmethod
from typing import Optional

from app.domain.fleet.entities.fleet_task import FleetTask


class IFleetTaskRepository(ABC):
    @abstractmethod
    def get_by_mission_code(self, mission_code: str) -> Optional[FleetTask]:
        raise NotImplementedError

    @abstractmethod
    def save(self, task: FleetTask) -> FleetTask:
        raise NotImplementedError
