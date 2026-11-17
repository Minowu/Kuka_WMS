"""Port: publish floor.changed events after dispatch actions."""

from abc import ABC, abstractmethod
from typing import List, Optional


class IFloorNotifier(ABC):
    @abstractmethod
    def notify_call_material_queued(
        self,
        *,
        request_code: str,
        location_ids: List[int],
        operator_id: Optional[int],
    ) -> None:
        raise NotImplementedError
