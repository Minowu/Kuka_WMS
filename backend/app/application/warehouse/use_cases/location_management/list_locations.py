"""Use case: list locations in a warehouse."""

from dataclasses import dataclass
from typing import List

from app.application.warehouse.ports.repositories.location_repository import ILocationRepository
from app.domain.warehouse.entities.location import Location


@dataclass
class ListLocationsRequest:
    warehouse_id: int
    active_only: bool = True


@dataclass
class ListLocationsResponse:
    locations: List[Location]


class ListLocationsUseCase:
    def __init__(self, location_repo: ILocationRepository):
        self._location_repo = location_repo

    def execute(self, request: ListLocationsRequest) -> ListLocationsResponse:
        if not request.warehouse_id:
            raise ValueError("Thiếu warehouse_id.")
        return ListLocationsResponse(
            locations=self._location_repo.list_by_warehouse(
                request.warehouse_id, active_only=request.active_only
            )
        )
