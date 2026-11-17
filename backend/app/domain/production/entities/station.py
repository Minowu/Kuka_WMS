"""Domain entity: Station slot / location used as CNC station view."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Station:
    """Logical station on the floor (often backed by a Location CNC_SLOT)."""

    id: Optional[int]
    location_code: str
    location_name: str
    location_type: str
    machine_id: Optional[int] = None
    position_index: Optional[int] = None
    is_active: bool = True

    def is_cnc_slot(self) -> bool:
        return self.location_type == "CNC_SLOT"
