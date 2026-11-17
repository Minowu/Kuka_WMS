"""Port: destination location lookup + occupancy guard."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DestinationLocationRef:
    id: int
    location_code: str
    machine_code: Optional[str] = None


class ILocationGuard(ABC):
    @abstractmethod
    def get_active_destination(self, location_id: int) -> DestinationLocationRef:
        """Raise ValueError if missing / inactive."""
        raise NotImplementedError

    @abstractmethod
    def ensure_location_free(self, location_id: int, location_code: str) -> None:
        """Raise ValueError if slot occupied or reserved by AMR."""
        raise NotImplementedError
