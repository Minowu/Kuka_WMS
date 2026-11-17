"""Ports for deep ReturnEmptyCartUseCase orchestration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class WashCartView:
    id: int
    container_code: str
    item_id: int
    location_id: int
    is_locked: bool
    locked_by_mission_code: Optional[str]


@dataclass
class WashLocationView:
    id: int
    location_code: str


@dataclass
class BufferSlotRef:
    id: int
    location_code: str


@dataclass
class ReturnRequestView:
    id: int
    request_code: str
    status: str
    container_id: Optional[int]
    destination_location_id: Optional[int]


class IWashCartLookup(ABC):
    @abstractmethod
    def get_wash_cart(self, container_code: str) -> WashCartView:
        raise NotImplementedError

    @abstractmethod
    def get_wash_location(self, location_id: int) -> WashLocationView:
        raise NotImplementedError


class IEmptyBufferFinder(ABC):
    @abstractmethod
    def find_next_empty_buffer_slot(self) -> Optional[BufferSlotRef]:
        raise NotImplementedError


class IReturnEmptyRequestWriter(ABC):
    @abstractmethod
    def create_return_empty(
        self,
        *,
        request_code: str,
        item_id: int,
        source_location_id: int,
        destination_location_id: int,
        container_id: int,
        status: str,
        priority: int,
        created_by: Optional[int],
    ) -> ReturnRequestView:
        raise NotImplementedError


class IReturnEmptyEventNotifier(ABC):
    @abstractmethod
    def notify_washing_released_queued(
        self, *, location_ids: List[int], container_code: str, operator_id: Optional[int]
    ) -> None:
        raise NotImplementedError
