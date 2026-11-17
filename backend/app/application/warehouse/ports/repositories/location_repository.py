from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.warehouse.entities.location import Location


class ILocationRepository(ABC):
    @abstractmethod
    def get_by_id(self, location_id: int) -> Optional[Location]:
        raise NotImplementedError

    @abstractmethod
    def list_by_warehouse(self, warehouse_id: int, active_only: bool = True) -> List[Location]:
        raise NotImplementedError
