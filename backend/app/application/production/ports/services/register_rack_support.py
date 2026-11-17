"""Ports for deep RegisterRackUseCase orchestration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RawMaterialLocationView:
    id: int
    location_code: str


@dataclass
class ItemView:
    id: int
    name: str
    sku: Optional[str]
    standard_quantity_per_cart: Optional[int]


@dataclass
class RegisteredCartView:
    id: int
    container_code: str
    item_id: int
    location_id: int
    quantity: int
    is_locked: bool
    locked_by_mission_code: Optional[str]
    destination_location_id: Optional[int]


class IRawMaterialLocationGuard(ABC):
    @abstractmethod
    def get_raw_material_location(self, location_id: int) -> RawMaterialLocationView:
        raise NotImplementedError

    @abstractmethod
    def assert_slot_free_for_container(self, location_id: int, container_code: str) -> None:
        raise NotImplementedError


class IItemCatalog(ABC):
    @abstractmethod
    def get_item(self, item_id: int) -> ItemView:
        raise NotImplementedError


class IRackAtRawMaterialRegistrar(ABC):
    @abstractmethod
    def upsert_rack(
        self,
        *,
        container_code: str,
        item_id: int,
        location_id: int,
        quantity: int,
    ) -> RegisteredCartView:
        raise NotImplementedError

    @abstractmethod
    def get_by_code(self, container_code: str) -> RegisteredCartView:
        raise NotImplementedError


class IFleetRackInserter(ABC):
    @abstractmethod
    def insert_rack(self, location_code: str, container_code: str) -> None:
        raise NotImplementedError


class IRegisterEventNotifier(ABC):
    @abstractmethod
    def notify_rack_registered(
        self, *, location_ids: List[int], container_code: str, operator_id: Optional[int]
    ) -> None:
        raise NotImplementedError
