"""Domain entity: ItemStock (warehouse stock row / container)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ItemStock:
    id: Optional[int]
    item_id: int
    quantity: float
    location_id: Optional[int] = None
    container_code: Optional[str] = None
    current_stage_level: int = 0
    status: str = "available"
    is_active: bool = True
    is_locked: bool = False
