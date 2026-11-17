from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MachineStageInfo:
    target_stage: int
    is_final_cnc: bool


class IMachineStageInfo(ABC):
    @abstractmethod
    def get_stage_info(self, location_id: int, item_id: int) -> MachineStageInfo:
        raise NotImplementedError
