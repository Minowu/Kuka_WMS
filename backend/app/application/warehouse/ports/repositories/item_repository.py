from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.warehouse.entities.item import Item


class IItemRepository(ABC):
    @abstractmethod
    def get_by_id(self, item_id: int) -> Optional[Item]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[Item]:
        raise NotImplementedError

    @abstractmethod
    def save(self, item: Item) -> Item:
        raise NotImplementedError
