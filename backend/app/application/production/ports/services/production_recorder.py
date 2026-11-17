from abc import ABC, abstractmethod
from typing import Optional


class IProductionRecorder(ABC):
    @abstractmethod
    def record_stage_completion(
        self,
        *,
        container_id: int,
        container_code: str,
        item_id: int,
        stage_level: int,
        location_id: int,
        machine_code: Optional[str],
        operator_id: Optional[int],
        notes: Optional[str],
    ) -> None:
        raise NotImplementedError
