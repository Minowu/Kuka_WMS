"""Use case: list product models (Items)."""

from dataclasses import dataclass
from typing import List

from app.application.warehouse.ports.repositories.item_repository import IItemRepository
from app.domain.warehouse.entities.item import Item


@dataclass
class ListItemsResponse:
    items: List[Item]


class ListItemsUseCase:
    def __init__(self, item_repo: IItemRepository):
        self._item_repo = item_repo

    def execute(self) -> ListItemsResponse:
        return ListItemsResponse(items=self._item_repo.list_all())
