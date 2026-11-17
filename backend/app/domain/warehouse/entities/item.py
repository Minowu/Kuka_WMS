"""Domain entity: Item / product model."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Item:
    id: Optional[int]
    sku: str
    name: str
    warehouse_id: int
    description: Optional[str] = None
    standard_quantity_per_cart: int = 120
    details: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = {}
