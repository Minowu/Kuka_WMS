"""Port: Machine repository."""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.production.entities.machine import Machine


class IMachineRepository(ABC):
    @abstractmethod
    def get_by_id(self, machine_id: int) -> Optional[Machine]:
        raise NotImplementedError

    @abstractmethod
    def get_by_code(self, machine_code: str) -> Optional[Machine]:
        raise NotImplementedError

    @abstractmethod
    def list_by_warehouse(self, warehouse_id: int) -> List[Machine]:
        raise NotImplementedError

    @abstractmethod
    def save(self, machine: Machine) -> Machine:
        raise NotImplementedError
