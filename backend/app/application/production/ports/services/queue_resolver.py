from abc import ABC, abstractmethod
from typing import Optional


class IQueueResolver(ABC):
    @abstractmethod
    def resolve_waiting_cart(self, stage_level: Optional[int] = None) -> int:
        raise NotImplementedError

    @abstractmethod
    def resolve_waiting_slot(self) -> int:
        raise NotImplementedError
