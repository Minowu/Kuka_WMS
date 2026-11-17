"""Domain entity: Warehouse Location."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Location:
    id: Optional[int]
    location_code: str
    location_name: str
    warehouse_id: int
    location_type: str = "UNASSIGNED"
    location_label: Optional[str] = None
    machine_id: Optional[int] = None
    position_index: Optional[int] = None
    is_active: bool = True

    def is_raw_material(self) -> bool:
        return self.location_type == "RAW_MATERIAL"
