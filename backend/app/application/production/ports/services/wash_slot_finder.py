from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SlotRef:
    id: int
    location_code: str


class IWashSlotFinder(ABC):
    @abstractmethod
    def find_available_wash_slot(self) -> Optional[SlotRef]:
        raise NotImplementedError


class IEmptyBufferFinder(ABC):
    @abstractmethod
    def find_next_empty_buffer_slot(self) -> Optional[SlotRef]:
        raise NotImplementedError
