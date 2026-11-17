"""Port: Rack / container repository."""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.production.entities.rack import Rack


class IRackRepository(ABC):
    @abstractmethod
    def get_by_id(self, rack_id: int) -> Optional[Rack]:
        raise NotImplementedError

    @abstractmethod
    def get_by_code(self, container_code: str) -> Optional[Rack]:
        raise NotImplementedError

    @abstractmethod
    def list_active(self, include_inactive: bool = False) -> List[Rack]:
        raise NotImplementedError

    @abstractmethod
    def save(self, rack: Rack) -> Rack:
        raise NotImplementedError
