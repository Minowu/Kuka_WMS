"""Use case: Register rack QR at raw-material location — deep port orchestration."""

from dataclasses import dataclass
from typing import Any, Optional

from app.application.production.ports.services.complete_stage_support import IUnitOfWork
from app.application.production.ports.services.queue_resolver import IQueueResolver
from app.application.production.ports.services.register_rack_support import (
    IFleetRackInserter,
    IItemCatalog,
    IRackAtRawMaterialRegistrar,
    IRawMaterialLocationGuard,
    IRegisterEventNotifier,
)
from app.domain.production.value_objects.rack_code import RackCode


@dataclass
class RegisterRackRequest:
    location_id: int
    item_id: int
    container_code: str
    quantity: Optional[int] = None
    lot_number: Optional[str] = None
    operator_id: Optional[int] = None


class RegisterRackUseCase:
    def __init__(
        self,
        location_guard: IRawMaterialLocationGuard,
        item_catalog: IItemCatalog,
        registrar: IRackAtRawMaterialRegistrar,
        fleet_inserter: IFleetRackInserter,
        queue_resolver: IQueueResolver,
        notifier: IRegisterEventNotifier,
        uow: IUnitOfWork,
    ):
        self._location_guard = location_guard
        self._item_catalog = item_catalog
        self._registrar = registrar
        self._fleet_inserter = fleet_inserter
        self._queue_resolver = queue_resolver
        self._notifier = notifier
        self._uow = uow

    def execute(self, request: RegisterRackRequest) -> dict[str, Any]:
        if not request.location_id:
            raise ValueError("Thiếu location_id khu nguyên liệu.")
        if not request.item_id:
            raise ValueError("Thiếu item_id (Model sản phẩm).")
        code = RackCode(request.container_code)

        location = self._location_guard.get_raw_material_location(request.location_id)
        self._location_guard.assert_slot_free_for_container(location.id, code.value)
        item = self._item_catalog.get_item(request.item_id)

        qty = (
            request.quantity
            if (request.quantity is not None and request.quantity > 0)
            else (item.standard_quantity_per_cart or 120)
        )

        cart = self._registrar.upsert_rack(
            container_code=code.value,
            item_id=item.id,
            location_id=location.id,
            quantity=qty,
        )

        try:
            self._fleet_inserter.insert_rack(location.location_code, code.value)
        except Exception as exc:
            self._uow.rollback()
            raise ValueError(f"KUKA Fleet từ chối tiếp nhận xe phôi: {exc}") from exc

        self._uow.flush()
        resolved = self._queue_resolver.resolve_waiting_cart(stage_level=0)
        loc_ids = sorted(
            {
                int(lid)
                for lid in (location.id, cart.destination_location_id)
                if lid is not None
            }
        )
        self._uow.commit()
        cart = self._registrar.get_by_code(code.value)
        self._notifier.notify_rack_registered(
            location_ids=loc_ids,
            container_code=code.value,
            operator_id=request.operator_id,
        )

        return {
            "success": True,
            "container_id": cart.id,
            "container_code": code.value,
            "item_id": item.id,
            "item_name": item.name,
            "sku": item.sku,
            "location_id": location.id,
            "location_code": location.location_code,
            "quantity": qty,
            "current_stage_level": 0,
            "is_locked": cart.is_locked,
            "fleet_inserted": True,
            "resolved_queue_count": resolved,
            "dispatched_mission_code": cart.locked_by_mission_code,
        }
