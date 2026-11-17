"""Port: register rack at raw-material location."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class IRegisterRackExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        *,
        location_id: int,
        item_id: int,
        container_code: str,
        quantity: Optional[int],
        lot_number: Optional[str],
        operator_id: Optional[int],
    ) -> dict[str, Any]:
        raise NotImplementedError
