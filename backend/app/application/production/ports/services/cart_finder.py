"""Port: find FIFO available cart for a CNC call."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AvailableCartRef:
    id: int
    container_code: str
    location_id: int


class ICartFinder(ABC):
    @abstractmethod
    def find_fifo_available_cart(
        self,
        item_id: int,
        stage_level: int,
        destination_location_id: int,
    ) -> Optional[AvailableCartRef]:
        raise NotImplementedError
