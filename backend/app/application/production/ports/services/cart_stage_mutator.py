from abc import ABC, abstractmethod
from typing import Optional


class ICartStageMutator(ABC):
    @abstractmethod
    def set_stage_level(self, cart_id: int, stage_level: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def mark_empty(self, cart_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_status(self, cart_id: int, status: str) -> None:
        raise NotImplementedError
