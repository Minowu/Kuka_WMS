"""Adapters for deep ReturnEmptyCartUseCase ports."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.application.production.ports.services.return_empty_support import (
    BufferSlotRef,
    IEmptyBufferFinder,
    IReturnEmptyEventNotifier,
    IReturnEmptyRequestWriter,
    IWashCartLookup,
    ReturnRequestView,
    WashCartView,
    WashLocationView,
)
from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.production_models import TransportRequest as TransportRequestORM
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids


class SqlAlchemyWashCartLookup(IWashCartLookup):
    def __init__(self, db: Session):
        self._db = db

    def get_wash_cart(self, container_code: str) -> WashCartView:
        cart = (
            self._db.query(ItemStock)
            .filter(ItemStock.container_code == container_code, ItemStock.is_active.is_(True))
            .first()
        )
        if not cart:
            raise ValueError(
                f"Không tìm thấy khay/xe '{container_code}' đang hoạt động tại khu Tẩy rửa."
            )
        if cart.is_locked:
            raise ValueError(
                f"Xe '{container_code}' đang bị khóa bởi nhiệm vụ '{cart.locked_by_mission_code}'."
            )
        return WashCartView(
            id=cart.id,
            container_code=cart.container_code,
            item_id=cart.item_id,
            location_id=cart.location_id,
            is_locked=bool(cart.is_locked),
            locked_by_mission_code=cart.locked_by_mission_code,
        )

    def get_wash_location(self, location_id: int) -> WashLocationView:
        loc = self._db.query(Location).filter(Location.id == location_id).first()
        if not loc or loc.location_type != "WASHING_SLOT":
            raise ValueError(
                "Xe không nằm tại vị trí Khu Tẩy Rửa (WASHING_SLOT)."
            )
        return WashLocationView(id=loc.id, location_code=loc.location_code)


class CartSelectorEmptyBufferFinder(IEmptyBufferFinder):
    def __init__(self, db: Session, selector: CartSelector):
        self._db = db
        self._selector = selector

    def find_next_empty_buffer_slot(self) -> Optional[BufferSlotRef]:
        slot = self._selector.find_next_empty_buffer_slot(self._db)
        if not slot:
            return None
        return BufferSlotRef(id=slot.id, location_code=slot.location_code)


class SqlAlchemyReturnEmptyRequestWriter(IReturnEmptyRequestWriter):
    def __init__(self, db: Session):
        self._db = db

    def create_return_empty(
        self,
        *,
        request_code: str,
        item_id: int,
        source_location_id: int,
        destination_location_id: int,
        container_id: int,
        status: str,
        priority: int,
        created_by: Optional[int],
    ) -> ReturnRequestView:
        orm = TransportRequestORM(
            request_code=request_code,
            request_type="RETURN_EMPTY_CART",
            item_id=item_id,
            source_location_id=source_location_id,
            destination_location_id=destination_location_id,
            container_id=container_id,
            required_stage_level=0,
            status=status,
            priority=priority,
            created_by=created_by,
        )
        self._db.add(orm)
        self._db.flush()
        return ReturnRequestView(
            id=orm.id,
            request_code=orm.request_code,
            status=orm.status,
            container_id=orm.container_id,
            destination_location_id=orm.destination_location_id,
        )


class ReturnEmptyEventNotifier(IReturnEmptyEventNotifier):
    def __init__(self, db: Session):
        self._db = db

    def notify_washing_released_queued(
        self, *, location_ids: List[int], container_code: str, operator_id: Optional[int]
    ) -> None:
        recipients = resolve_location_recipient_user_ids(
            self._db, location_ids, extra_user_ids=[operator_id]
        )
        publish_event(
            "floor.changed",
            {
                "reason": "washing_released_queued",
                "location_ids": location_ids,
                "container_code": container_code,
            },
            user_ids=recipients,
            admins=True,
        )
