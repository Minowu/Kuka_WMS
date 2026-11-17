"""DI factories for fleet / warehouse use cases."""

from typing import Optional

from sqlalchemy.orm import Session

from app.application.fleet.ports.fleet_task_repository import IFleetTaskRepository
from app.application.fleet.use_cases.handle_webhook import HandleWebhookUseCase
from app.application.fleet.use_cases.submit_task import SubmitTaskUseCase
from app.application.warehouse.use_cases.item_management.get_item import GetItemUseCase
from app.application.warehouse.use_cases.item_management.list_items import ListItemsUseCase
from app.application.warehouse.use_cases.location_management.list_locations import (
    ListLocationsUseCase,
)
from app.domain.fleet.entities.fleet_task import FleetTask
from app.infrastructure.di.production_factory import build_handle_webhook_use_case
from app.infrastructure.external_services.fleet.fleet_submitter_adapter import (
    FleetSubmitterAdapter,
)
from app.infrastructure.persistence.sqlalchemy.repositories.fleet.fleet_task_repository_impl import (
    FleetTaskRepositoryImpl,
)
from app.infrastructure.persistence.sqlalchemy.repositories.warehouse.item_repository_impl import (
    ItemRepositoryImpl,
)
from app.infrastructure.persistence.sqlalchemy.repositories.warehouse.location_repository_impl import (
    LocationRepositoryImpl,
)


class _NullFleetTaskRepo(IFleetTaskRepository):
    def get_by_mission_code(self, mission_code: str) -> Optional[FleetTask]:
        return None

    def save(self, task: FleetTask) -> FleetTask:
        return task


def get_submit_task_use_case(db: Optional[Session] = None) -> SubmitTaskUseCase:
    # Submit path uses short-lived sessions inside the adapter.
    if db is None:
        return SubmitTaskUseCase(
            fleet_task_repo=_NullFleetTaskRepo(),
            fleet_submitter=FleetSubmitterAdapter(),
        )
    return SubmitTaskUseCase(
        fleet_task_repo=FleetTaskRepositoryImpl(db),
        fleet_submitter=FleetSubmitterAdapter(),
    )


def get_list_items_use_case(db: Session) -> ListItemsUseCase:
    return ListItemsUseCase(item_repo=ItemRepositoryImpl(db))


def get_get_item_use_case(db: Session) -> GetItemUseCase:
    return GetItemUseCase(item_repo=ItemRepositoryImpl(db))


def get_list_locations_use_case(db: Session) -> ListLocationsUseCase:
    return ListLocationsUseCase(location_repo=LocationRepositoryImpl(db))


def get_handle_webhook_use_case(db: Session) -> HandleWebhookUseCase:
    return build_handle_webhook_use_case(db)
