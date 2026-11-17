"""Port: execute CNC complete-stage workflow."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class ICompleteStageExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        *,
        container_code: Optional[str],
        location_id: Optional[int],
        operator_id: Optional[int],
        notes: Optional[str],
    ) -> dict[str, Any]:
        raise NotImplementedError
