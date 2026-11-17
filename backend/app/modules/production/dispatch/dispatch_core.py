"""Core Production Operations facade — delegates to ops modules."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient
from app.modules.production.dispatch.ops import (
    call_material as call_material_ops,
    complete_stage as complete_stage_ops,
    fleet_lock as fleet_lock_ops,
    raw_material_registration as raw_material_ops,
    return_empty_cart as return_empty_ops,
    user_location_assign as user_location_ops,
)
from app.modules.production.dispatch.queue_service import QueueService
from app.modules.production.production_models import FleetTask, TransportRequest, UserLocation
from app.modules.warehouse.item_stock.item_stock_model import ItemStock


class DispatchCore:
    """Orchestrates production floor dispatch actions and coordinates sub-services."""

    def __init__(
        self,
        fleet_client: KukaFleetClient,
        selector: CartSelector,
        queue_service: QueueService,
    ):
        self.fleet_client = fleet_client
        self.selector = selector
        self.queue_service = queue_service

    def assign_locations_to_user(
        self,
        db: Session,
        user_id: int,
        location_ids: list[int],
    ) -> list[UserLocation]:
        return user_location_ops.assign_locations_to_user(self, db, user_id, location_ids)

    def lock_cart_and_dispatch_fleet_task(
        self,
        db: Session,
        transport_req: TransportRequest,
        cart: ItemStock,
        pickup_location_id: int,
        dropoff_location_id: int,
    ) -> FleetTask:
        return fleet_lock_ops.lock_cart_and_dispatch_fleet_task(
            self, db, transport_req, cart, pickup_location_id, dropoff_location_id
        )

    def register_rack_at_raw_material(self, *args, **kwargs) -> dict[str, Any]:
        return raw_material_ops.register_rack_at_raw_material(self, *args, **kwargs)

    def call_material_to_cnc(self, *args, **kwargs) -> TransportRequest:
        return call_material_ops.call_material_to_cnc(self, *args, **kwargs)

    def complete_machining_stage(self, *args, **kwargs) -> dict[str, Any]:
        return complete_stage_ops.complete_machining_stage(self, *args, **kwargs)

    def complete_washing_and_return_empty_cart(self, *args, **kwargs) -> TransportRequest:
        return return_empty_ops.complete_washing_and_return_empty_cart(self, *args, **kwargs)

    def call_empty_cart_async(
        self,
        db: Session,
        container_code: str,
        operator_id: Optional[int] = None,
    ) -> TransportRequest:
        return self.complete_washing_and_return_empty_cart(db, container_code, operator_id)

    def call_material_cart_async(
        self,
        db: Session,
        destination_location_id: int,
        item_id: Optional[int] = None,
        required_stage_level: Optional[int] = None,
        created_by: Optional[int] = None,
        priority: int = 10,
    ) -> TransportRequest:
        return self.call_material_to_cnc(
            db, destination_location_id, item_id, required_stage_level, created_by, priority
        )

    def dispatch_transport_request(
        self,
        db: Session,
        transport_req: TransportRequest,
        cart: ItemStock,
        pickup_location_id: int,
        dropoff_location_id: int,
    ) -> FleetTask:
        return self.lock_cart_and_dispatch_fleet_task(
            db, transport_req, cart, pickup_location_id, dropoff_location_id
        )
