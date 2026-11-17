"""Infrastructure adapters for CallMaterialUseCase ports."""

from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from app.application.production.ports.services.cart_finder import AvailableCartRef, ICartFinder
from app.application.production.ports.services.fleet_dispatcher import IFleetDispatcher
from app.application.production.ports.services.floor_notifier import IFloorNotifier
from app.application.production.ports.services.location_guard import (
    DestinationLocationRef,
    ILocationGuard,
)
from app.application.production.ports.services.stage_resolver import IStageResolver
from app.application.production.ports.services.transport_queue import ITransportQueue
from app.application.production.ports.services.unit_of_work_port import ICallMaterialUnitOfWork
from app.domain.production.entities.transport_request import TransportRequest
from app.infrastructure.persistence.sqlalchemy.mappers.production_mapper import (
    transport_request_to_domain,
)
from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.dispatch.queue_service import QueueService
from app.modules.production.production_models import TransportRequest as TransportRequestORM
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids


class SqlAlchemyLocationGuard(ILocationGuard):
    def __init__(self, db: Session, selector: CartSelector):
        self._db = db
        self._selector = selector

    def get_active_destination(self, location_id: int) -> DestinationLocationRef:
        loc = (
            self._db.query(Location)
            .filter(Location.id == location_id, Location.is_active.is_(True))
            .first()
        )
        if not loc:
            raise ValueError("Vị trí đích (Location) không tồn tại hoặc đã bị khóa.")
        machine_code = loc.machine.machine_code if getattr(loc, "machine", None) else None
        return DestinationLocationRef(
            id=loc.id,
            location_code=loc.location_code,
            machine_code=machine_code,
        )

    def ensure_location_free(self, location_id: int, location_code: str) -> None:
        if not self._selector.is_location_free(self._db, location_id):
            raise ValueError(
                f"Vị trí '{location_code}' hiện đang có xe hoặc đã có AMR đặt chỗ. "
                f"Vui lòng chọn vị trí trống."
            )


class CartSelectorStageResolver(IStageResolver):
    def __init__(self, db: Session, selector: CartSelector):
        self._db = db
        self._selector = selector

    def resolve_required_stage(self, location_id: int, item_id: int) -> int:
        loc = self._db.query(Location).filter(Location.id == location_id).first()
        if not loc:
            raise ValueError("Vị trí đích (Location) không tồn tại hoặc đã bị khóa.")
        input_lvl, _, _ = self._selector.get_stage_info_for_machine(self._db, loc, item_id)
        return input_lvl


class CartSelectorFinder(ICartFinder):
    def __init__(self, db: Session, selector: CartSelector):
        self._db = db
        self._selector = selector

    def find_fifo_available_cart(
        self,
        item_id: int,
        stage_level: int,
        destination_location_id: int,
    ) -> Optional[AvailableCartRef]:
        loc = self._db.query(Location).filter(Location.id == destination_location_id).first()
        cart = self._selector.find_fifo_available_cart(
            self._db,
            item_id=item_id,
            stage_level=stage_level,
            target_location=loc,
        )
        if not cart:
            return None
        return AvailableCartRef(
            id=cart.id,
            container_code=cart.container_code,
            location_id=cart.location_id,
        )


class QueueServiceTransportQueue(ITransportQueue):
    def __init__(self, db: Session, queue_service: QueueService):
        self._db = db
        self._queue_service = queue_service

    def enqueue_waiting_cart(
        self,
        request_id: int,
        target_stage_level: Optional[int],
        priority: int,
    ) -> None:
        self._queue_service.enqueue(
            db=self._db,
            request_id=request_id,
            queue_type="WAITING_CART",
            target_stage_level=target_stage_level,
            priority=priority,
        )


class LockCartFleetDispatcher(IFleetDispatcher):
    def __init__(
        self,
        db: Session,
        lock_fn: Callable[..., object],
    ):
        self._db = db
        self._lock_fn = lock_fn

    def lock_cart_and_dispatch(
        self,
        transport_request_id: int,
        cart_id: int,
        pickup_location_id: int,
        dropoff_location_id: int,
    ) -> None:
        transport_req = (
            self._db.query(TransportRequestORM)
            .filter(TransportRequestORM.id == transport_request_id)
            .first()
        )
        cart = self._db.query(ItemStock).filter(ItemStock.id == cart_id).first()
        if not transport_req or not cart:
            raise ValueError("Không tìm thấy TransportRequest hoặc cart để dispatch.")
        self._lock_fn(
            self._db,
            transport_req,
            cart,
            pickup_location_id,
            dropoff_location_id,
        )


class EventBusFloorNotifier(IFloorNotifier):
    def __init__(self, db: Session):
        self._db = db

    def notify_call_material_queued(
        self,
        *,
        request_code: str,
        location_ids: List[int],
        operator_id: Optional[int],
    ) -> None:
        recipient_user_ids = resolve_location_recipient_user_ids(
            self._db,
            location_ids,
            extra_user_ids=[operator_id],
        )
        publish_event(
            "floor.changed",
            {
                "reason": "call_material_queued",
                "request_code": request_code,
                "location_ids": location_ids,
            },
            user_ids=recipient_user_ids,
            admins=True,
        )


class SqlAlchemyCallMaterialUnitOfWork(ICallMaterialUnitOfWork):
    def __init__(self, db: Session):
        self._db = db

    def commit(self) -> None:
        self._db.commit()

    def refresh_transport_request(self, request_id: int) -> TransportRequest:
        orm = (
            self._db.query(TransportRequestORM)
            .filter(TransportRequestORM.id == request_id)
            .first()
        )
        if not orm:
            raise ValueError(f"TransportRequest id={request_id} not found after commit")
        self._db.refresh(orm)
        return transport_request_to_domain(orm)
