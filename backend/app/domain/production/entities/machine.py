"""Domain entity: CNC Machine (pure, no ORM)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Machine:
    id: Optional[int]
    machine_code: str
    machine_name: str
    warehouse_id: Optional[int]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def display_name(self) -> str:
        return self.machine_name or self.machine_code
