"""Domain entity: Rack / container (logical view over ItemStock)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Rack:
    id: Optional[int]
    container_code: str
    item_id: Optional[int]
    location_id: Optional[int]
    quantity: int
    current_stage_level: int
    status: str
    is_active: bool = True
    is_locked: bool = False
    locked_by_mission_code: Optional[str] = None
    destination_location_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def can_be_dispatched(self) -> bool:
        return self.is_active and not self.is_locked

    def lock(self, mission_code: str, destination_location_id: int) -> None:
        if self.is_locked:
            raise ValueError(
                f"Rack '{self.container_code}' đang bị khóa bởi '{self.locked_by_mission_code}'."
            )
        self.is_locked = True
        self.locked_by_mission_code = mission_code
        self.destination_location_id = destination_location_id
