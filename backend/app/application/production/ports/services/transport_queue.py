"""Port: enqueue transport requests waiting for cart/slot."""

from abc import ABC, abstractmethod
from typing import Optional


class ITransportQueue(ABC):
    @abstractmethod
    def enqueue_waiting_cart(
        self,
        request_id: int,
        target_stage_level: Optional[int],
        priority: int,
    ) -> None:
        raise NotImplementedError
