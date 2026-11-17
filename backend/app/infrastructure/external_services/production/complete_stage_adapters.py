"""Adapters for deep CompleteStageUseCase ports."""

from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from app.application.production.ports.services.active_cart_lookup import (
    ActiveCartView,
    CartLocationView,
    IActiveCartLookup,
)
from app.application.production.ports.services.cart_stage_mutator import ICartStageMutator
from app.application.production.ports.services.complete_stage_support import (
    IMoveToWashRequestWriter,
    IStageEventNotifier,
    IUnitOfWork,
    IWaitingSlotQueue,
)
from app.application.production.ports.services.machine_stage_info import (
    IMachineStageInfo,
    MachineStageInfo,
)
from app.application.production.ports.services.production_recorder import IProductionRecorder
from app.application.production.ports.services.queue_resolver import IQueueResolver
from app.application.production.ports.services.wash_slot_finder import IWashSlotFinder, SlotRef
from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.dispatch.queue_service import QueueService
from app.modules.production.production_models import (
    ProductionRecord,
    TransportRequest as TransportRequestORM,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids


class SqlAlchemyActiveCartLookup(IActiveCartLookup):
    def __init__(self, db: Session):
        self._db = db

    def get_active_cart(
        self,
        *,
        container_code: Optional[str],
        location_id: Optional[int],
    ) -> ActiveCartView:
        cart = None
        if container_code:
            cart = (
                self._db.query(ItemStock)
                .filter(
                    ItemStock.container_code == container_code.strip(),
                    ItemStock.is_active.is_(True),
                )
                .first()
            )
        elif location_id:
            cart = (
                self._db.query(ItemStock)
                .filter(ItemStock.location_id == location_id, ItemStock.is_active.is_(True))
                .first()
            )
        if not cart:
            target = f"mã '{container_code}'" if container_code else f"vị trí ID={location_id}"
            raise ValueError(f"Không tìm thấy khay phôi (ItemStock) đang hoạt động tại {target}.")
        if cart.is_locked:
            raise ValueError(
                f"Khay phôi '{cart.container_code}' đang bị khóa bởi nhiệm vụ "
                f"'{cart.locked_by_mission_code}'."
            )
        if not cart.location_id:
            raise ValueError(f"Vị trí của khay phôi '{cart.container_code}' không hợp lệ.")
        return ActiveCartView(
            id=cart.id,
            container_code=cart.container_code,
            item_id=cart.item_id,
            location_id=cart.location_id,
            current_stage_level=cart.current_stage_level or 0,
            is_locked=bool(cart.is_locked),
            locked_by_mission_code=cart.locked_by_mission_code,
        )

    def get_cart_location(self, location_id: int) -> CartLocationView:
        loc = self._db.query(Location).filter(Location.id == location_id).first()
        if not loc:
            raise ValueError("Vị trí của khay phôi không hợp lệ.")
        machine_code = loc.machine.machine_code if getattr(loc, "machine", None) else None
        return CartLocationView(
            id=loc.id, location_code=loc.location_code, machine_code=machine_code
        )


class CartSelectorMachineStageInfo(IMachineStageInfo):
    def __init__(self, db: Session, selector: CartSelector):
        self._db = db
        self._selector = selector

    def get_stage_info(self, location_id: int, item_id: int) -> MachineStageInfo:
        loc = self._db.query(Location).filter(Location.id == location_id).first()
        if not loc:
            raise ValueError("Vị trí không hợp lệ.")
        _, target_stage, is_final = self._selector.get_stage_info_for_machine(
            self._db, loc, item_id
        )
        return MachineStageInfo(target_stage=target_stage, is_final_cnc=bool(is_final))


class SqlAlchemyProductionRecorder(IProductionRecorder):
    def __init__(self, db: Session):
        self._db = db

    def record_stage_completion(
        self,
        *,
        container_id: int,
        container_code: str,
        item_id: int,
        stage_level: int,
        location_id: int,
        machine_code: Optional[str],
        operator_id: Optional[int],
        notes: Optional[str],
    ) -> None:
        self._db.add(
            ProductionRecord(
                container_id=container_id,
                container_code=container_code,
                item_id=item_id,
                stage_level=stage_level,
                location_id=location_id,
                machine_code=machine_code,
                operator_id=operator_id,
                notes=notes,
            )
        )


class SqlAlchemyCartStageMutator(ICartStageMutator):
    def __init__(self, db: Session):
        self._db = db

    def _cart(self, cart_id: int) -> ItemStock:
        cart = self._db.query(ItemStock).filter(ItemStock.id == cart_id).first()
        if not cart:
            raise ValueError(f"Cart id={cart_id} not found")
        return cart

    def set_stage_level(self, cart_id: int, stage_level: int) -> None:
        self._cart(cart_id).current_stage_level = stage_level

    def mark_empty(self, cart_id: int) -> None:
        cart = self._cart(cart_id)
        cart.quantity = 0
        cart.status = "empty"
        cart.current_stage_level = 0

    def set_status(self, cart_id: int, status: str) -> None:
        self._cart(cart_id).status = status


class CartSelectorWashSlotFinder(IWashSlotFinder):
    def __init__(self, db: Session, selector: CartSelector):
        self._db = db
        self._selector = selector

    def find_available_wash_slot(self) -> Optional[SlotRef]:
        slot = self._selector.find_available_slot_to_wash(self._db)
        if not slot:
            return None
        return SlotRef(id=slot.id, location_code=slot.location_code)


class QueueServiceResolver(IQueueResolver):
    def __init__(self, db: Session, queue_service: QueueService, lock_fn: Callable[..., object]):
        self._db = db
        self._queue_service = queue_service
        self._lock_fn = lock_fn

    def resolve_waiting_cart(self, stage_level: Optional[int] = None) -> int:
        return self._queue_service.try_resolve_waiting_cart_queue(
            self._db, stage_level=stage_level, lock_and_dispatch_fn=self._lock_fn
        )

    def resolve_waiting_slot(self) -> int:
        return self._queue_service.try_resolve_waiting_slot_queue(
            self._db, lock_and_dispatch_fn=self._lock_fn
        )


class WaitingSlotQueueAdapter(IWaitingSlotQueue):
    def __init__(self, db: Session, queue_service: QueueService):
        self._db = db
        self._queue_service = queue_service

    def enqueue_waiting_slot(
        self, request_id: int, target_stage_level: Optional[int], priority: int
    ) -> None:
        self._queue_service.enqueue(
            db=self._db,
            request_id=request_id,
            queue_type="WAITING_SLOT",
            target_stage_level=target_stage_level,
            priority=priority,
        )


class StageEventNotifier(IStageEventNotifier):
    def __init__(self, db: Session):
        self._db = db

    def notify_stage_completed(
        self, *, location_ids: List[int], container_code: str, operator_id: Optional[int]
    ) -> None:
        self._publish(
            "stage_completed",
            {"location_ids": location_ids, "container_code": container_code},
            location_ids,
            operator_id,
        )

    def notify_stage_queued_wash(
        self, *, location_ids: List[int], container_code: str, operator_id: Optional[int]
    ) -> None:
        self._publish(
            "stage_completed_queued_wash",
            {"location_ids": location_ids, "container_code": container_code},
            location_ids,
            operator_id,
        )

    def _publish(self, reason: str, data: dict, location_ids: List[int], operator_id: Optional[int]):
        recipients = resolve_location_recipient_user_ids(
            self._db, location_ids, extra_user_ids=[operator_id]
        )
        publish_event("floor.changed", {"reason": reason, **data}, user_ids=recipients, admins=True)


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, db: Session):
        self._db = db

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()

    def flush(self) -> None:
        self._db.flush()


class MoveToWashRequestWriter(IMoveToWashRequestWriter):
    def __init__(self, db: Session):
        self._db = db

    def create_move_to_wash(
        self,
        *,
        request_code: str,
        item_id: int,
        source_location_id: int,
        destination_location_id: int,
        container_id: int,
        required_stage_level: int,
        status: str,
        priority: int,
        created_by: Optional[int],
    ) -> int:
        orm = TransportRequestORM(
            request_code=request_code,
            request_type="MOVE_TO_WASH",
            item_id=item_id,
            source_location_id=source_location_id,
            destination_location_id=destination_location_id,
            container_id=container_id,
            required_stage_level=required_stage_level,
            status=status,
            priority=priority,
            created_by=created_by,
        )
        self._db.add(orm)
        self._db.flush()
        return orm.id
