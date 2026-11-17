"""Use case: get one product model by id."""

from dataclasses import dataclass
from typing import Optional

from app.application.warehouse.ports.repositories.item_repository import IItemRepository
from app.domain.warehouse.entities.item import Item


@dataclass
class GetItemRequest:
    item_id: int


@dataclass
class GetItemResponse:
    item: Optional[Item]


class GetItemUseCase:
    def __init__(self, item_repo: IItemRepository):
        self._item_repo = item_repo

    def execute(self, request: GetItemRequest) -> GetItemResponse:
        if not request.item_id:
            raise ValueError("Thiếu item_id.")
        return GetItemResponse(item=self._item_repo.get_by_id(request.item_id))
