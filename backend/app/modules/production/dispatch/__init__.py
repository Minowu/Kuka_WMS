"""Dispatch Service Facade - exports unified dispatch_service maintaining 100% backward compatibility."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.dispatch.dispatch_core import DispatchCore
from app.modules.production.dispatch.kuka_fleet_client import IcsError, KukaFleetClient
from app.modules.production.dispatch.queue_service import QueueService
from app.modules.production.dispatch.webhook_handler import WebhookHandler
from app.modules.production.production_models import (
    FleetTask,
    TaskStatus,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location


class DispatchService:
    """Facade orchestrating all modularized production dispatch sub-services."""

    def __init__(self):
        self.fleet_client = KukaFleetClient()
        self.selector = CartSelector()
        self.queue_service = QueueService(self.selector)
        self.core = DispatchCore(self.fleet_client, self.selector, self.queue_service)
        self.webhook_handler = WebhookHandler(self.fleet_client)

    # --- KUKA Fleet Client Delegations ---
    def _post_kuka(self, *args, **kwargs):
        return self.fleet_client._post_kuka(*args, **kwargs)

    def add_task(self, *args, **kwargs):
        return self.fleet_client.add_task(*args, **kwargs)

    def fleet_container_in(self, *args, **kwargs):
        return self.fleet_client.fleet_container_in(*args, **kwargs)

    def fleet_insert_rack(self, *args, **kwargs):
        return self.fleet_client.fleet_insert_rack(*args, **kwargs)

    def fleet_container_out(self, *args, **kwargs):
        return self.fleet_client.fleet_container_out(*args, **kwargs)

    def fleet_remove_rack(self, *args, **kwargs):
        return self.fleet_client.fleet_remove_rack(*args, **kwargs)

    def fleet_cancel_task(self, *args, **kwargs):
        return self.fleet_client.fleet_cancel_task(*args, **kwargs)

    def fleet_move_material(self, *args, **kwargs):
        return self.fleet_client.fleet_move_material(*args, **kwargs)

    def fleet_move_to_wash(self, *args, **kwargs):
        return self.fleet_client.fleet_move_to_wash(*args, **kwargs)

    def fleet_move_empty_container(self, *args, **kwargs):
        return self.fleet_client.fleet_move_empty_container(*args, **kwargs)

    def fleet_move_empty_rack(self, *args, **kwargs):
        return self.fleet_client.fleet_move_empty_rack(*args, **kwargs)

    def submit_fleet_task(self, *args, **kwargs):
        return self.fleet_client.submit_fleet_task(*args, **kwargs)

    def create_fleet_task(self, db: Session, task: FleetTask, request_type: str = "CALL_MATERIAL") -> FleetTask:
        return self.submit_fleet_task(db, task, request_type=request_type)

    # --- Cart Selector Delegations ---
    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        return self.selector.calculate_distance(loc1, loc2)

    def get_stage_info_for_machine(self, db: Session, location: Location, item_id: int):
        return self.selector.get_stage_info_for_machine(db, location, item_id)

    def find_fifo_available_cart(self, db: Session, item_id: int, stage_level: int = 0, target_location: Optional[Location] = None):
        return self.selector.find_fifo_available_cart(db, item_id, stage_level, target_location)

    def _is_location_free(self, db: Session, location_id: int) -> bool:
        return self.selector.is_location_free(db, location_id)

    def find_available_slot_to_wash(self, db: Session) -> Optional[Location]:
        return self.selector.find_available_slot_to_wash(db)

    def find_next_empty_buffer_slot(self, db: Session) -> Optional[Location]:
        return self.selector.find_next_empty_buffer_slot(db)

    # --- Core Dispatch Delegations ---
    def assign_locations_to_user(self, db: Session, user_id: int, location_ids: list[int]) -> list[UserLocation]:
        return self.core.assign_locations_to_user(db, user_id, location_ids)

    def _lock_cart_and_dispatch_fleet_task(
        self,
        db: Session,
        transport_req: TransportRequest,
        cart: ItemStock,
        pickup_location_id: int,
        dropoff_location_id: int,
    ) -> FleetTask:
        return self.core.lock_cart_and_dispatch_fleet_task(
            db, transport_req, cart, pickup_location_id, dropoff_location_id
        )

    def register_rack_at_raw_material(self, *args, **kwargs) -> dict[str, Any]:
        return self.core.register_rack_at_raw_material(*args, **kwargs)

    def call_material_to_cnc(self, *args, **kwargs) -> TransportRequest:
        return self.core.call_material_to_cnc(*args, **kwargs)

    def complete_machining_stage(self, *args, **kwargs) -> dict[str, Any]:
        return self.core.complete_machining_stage(*args, **kwargs)

    def complete_washing_and_return_empty_cart(self, *args, **kwargs) -> TransportRequest:
        return self.core.complete_washing_and_return_empty_cart(*args, **kwargs)

    # --- Webhook & Completion Delegations ---
    def receive_task_status(self, db: Session, payload: dict[str, Any]) -> Optional[TaskStatus]:
        return self.webhook_handler.receive_task_status(
            db=db,
            payload=payload,
            on_completed_fn=self.complete_fleet_task,
        )

    def complete_fleet_task(self, db: Session, mission_code: str) -> FleetTask:
        return self.webhook_handler.complete_fleet_task(
            db=db,
            mission_code=mission_code,
            on_after_complete_fn=self.scan_all_transport_queues,
        )

    # --- Queue & Always-Scan Delegations ---
    def try_resolve_waiting_cart_queue(self, db: Session, stage_level: Optional[int] = None) -> int:
        return self.queue_service.try_resolve_waiting_cart_queue(
            db=db,
            stage_level=stage_level,
            lock_and_dispatch_fn=self.core.lock_cart_and_dispatch_fleet_task,
        )

    def try_resolve_waiting_slot_queue(self, db: Session) -> int:
        return self.queue_service.try_resolve_waiting_slot_queue(
            db=db,
            lock_and_dispatch_fn=self.core.lock_cart_and_dispatch_fleet_task,
        )

    def scan_all_transport_queues(self, db: Session) -> dict[str, int]:
        resolved_carts = self.try_resolve_waiting_cart_queue(db, stage_level=None)
        resolved_slots = self.try_resolve_waiting_slot_queue(db)
        return {
            "resolved_waiting_cart": resolved_carts,
            "resolved_waiting_slot": resolved_slots,
        }


dispatch_service = DispatchService()

__all__ = ["DispatchService", "dispatch_service", "IcsError"]
