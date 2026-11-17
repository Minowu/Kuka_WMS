"""Domain entities: ProductionRoute / RouteStep."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RouteStep:
    id: Optional[int]
    route_id: Optional[int]
    step_number: int
    stage_level: int
    step_name: str
    is_final_cnc_step: bool = False
    machine_ids: List[int] = field(default_factory=list)

    def input_stage_level(self) -> int:
        return max(self.stage_level - 1, 0)


@dataclass
class ProductionRoute:
    id: Optional[int]
    route_code: str
    route_name: str
    item_id: int
    version: int = 1
    is_active: bool = True
    steps: List[RouteStep] = field(default_factory=list)

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    def final_step(self) -> Optional[RouteStep]:
        finals = [s for s in self.steps if s.is_final_cnc_step]
        return finals[0] if finals else (self.steps[-1] if self.steps else None)
