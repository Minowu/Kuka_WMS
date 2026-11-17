from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActiveCartView:
    id: int
    container_code: str
    item_id: int
    location_id: int
    current_stage_level: int
    is_locked: bool
    locked_by_mission_code: Optional[str] = None


@dataclass
class CartLocationView:
    id: int
    location_code: str
    machine_code: Optional[str] = None


class IActiveCartLookup(ABC):
    @abstractmethod
    def get_active_cart(
        self,
        *,
        container_code: Optional[str],
        location_id: Optional[int],
    ) -> ActiveCartView:
        raise NotImplementedError

    @abstractmethod
    def get_cart_location(self, location_id: int) -> CartLocationView:
        raise NotImplementedError
