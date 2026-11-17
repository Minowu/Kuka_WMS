"""Port: return empty cart from washing to buffer."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class IReturnEmptyCartExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        *,
        container_code: str,
        operator_id: Optional[int],
    ) -> Any:
        """Return transport-request-like object with id/request_code/status/..."""
        raise NotImplementedError
