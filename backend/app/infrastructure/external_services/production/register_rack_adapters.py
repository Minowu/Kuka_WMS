"""Adapters for deep RegisterRackUseCase ports."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.application.production.ports.services.register_rack_support import (
    IFleetRackInserter,
    IItemCatalog,
    IRackAtRawMaterialRegistrar,
    IRawMaterialLocationGuard,
    IRegisterEventNotifier,
    ItemView,
    RawMaterialLocationView,
    RegisteredCartView,
)
from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids


class SqlAlchemyRawMaterialLocationGuard(IRawMaterialLocationGuard):
    def __init__(self, db: Session):
        self._db = db

    def get_raw_material_location(self, location_id: int) -> RawMaterialLocationView:
        location = (
            self._db.query(Location)
            .filter(Location.id == location_id, Location.is_active.is_(True))
            .first()
        )
        if not location:
            raise ValueError(
                f"Vị trí cấp phôi (ID={location_id}) không tồn tại hoặc đã bị khóa."
            )
        if location.location_type != "RAW_MATERIAL":
            raise ValueError(
                f"Vị trí '{location.location_code}' không phải là vị trí Khu Nguyên Liệu (RAW_MATERIAL)."
            )
        return RawMaterialLocationView(id=location.id, location_code=location.location_code)

    def assert_slot_free_for_container(self, location_id: int, container_code: str) -> None:
        location = self._db.query(Location).filter(Location.id == location_id).first()
        occupying = (
            self._db.query(ItemStock)
            .filter(
                ItemStock.location_id == location_id,
                ItemStock.is_active.is_(True),
                ItemStock.container_code != container_code,
            )
            .first()
        )
        if occupying:
            code = location.location_code if location else str(location_id)
            raise ValueError(
                f"Vị trí '{code}' đang có xe/rack '{occupying.container_code}' đỗ."
            )


class SqlAlchemyItemCatalog(IItemCatalog):
    def __init__(self, db: Session):
        self._db = db

    def get_item(self, item_id: int) -> ItemView:
        item = self._db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise ValueError(
                f"Model sản phẩm ID={item_id} không tồn tại hoặc đã ngừng hoạt động."
            )
        return ItemView(
            id=item.id,
            name=item.name,
            sku=getattr(item, "sku", None),
            standard_quantity_per_cart=item.standard_quantity_per_cart,
        )


class SqlAlchemyRackAtRawMaterialRegistrar(IRackAtRawMaterialRegistrar):
    def __init__(self, db: Session):
        self._db = db

    def upsert_rack(
        self,
        *,
        container_code: str,
        item_id: int,
        location_id: int,
        quantity: int,
    ) -> RegisteredCartView:
        cart = (
            self._db.query(ItemStock)
            .filter(ItemStock.container_code == container_code)
            .first()
        )
        now = datetime.now(timezone.utc)
        if cart:
            if cart.is_locked:
                raise ValueError(
                    f"Rack '{container_code}' đang bị khóa bởi tác vụ vận chuyển "
                    f"'{cart.locked_by_mission_code}'."
                )
            if cart.is_active and cart.location_id and cart.location_id != location_id:
                curr_loc = (
                    self._db.query(Location)
                    .filter(Location.id == cart.location_id)
                    .first()
                )
                loc_name = curr_loc.location_code if curr_loc else f"ID={cart.location_id}"
                raise ValueError(
                    f"Rack '{container_code}' hiện đang hoạt động tại vị trí '{loc_name}'. "
                    f"Cần hoàn thành chu trình trước khi đăng ký lại ở Phôi Thô."
                )
            cart.item_id = item_id
            cart.location_id = location_id
            cart.destination_location_id = None
            cart.quantity = quantity
            cart.current_stage_level = 0
            cart.status = "available"
            cart.is_active = True
            cart.is_locked = False
            cart.locked_by_mission_code = None
            cart.fleet_registered = True
            cart.created_at = now
        else:
            cart = ItemStock(
                container_code=container_code,
                item_id=item_id,
                location_id=location_id,
                quantity=quantity,
                current_stage_level=0,
                status="available",
                is_active=True,
                is_locked=False,
                fleet_registered=True,
                created_at=now,
            )
            self._db.add(cart)
            self._db.flush()

        return self._to_view(cart)

    def get_by_code(self, container_code: str) -> RegisteredCartView:
        cart = (
            self._db.query(ItemStock)
            .filter(ItemStock.container_code == container_code)
            .first()
        )
        if not cart:
            raise ValueError(f"Rack '{container_code}' không tồn tại sau đăng ký.")
        self._db.refresh(cart)
        return self._to_view(cart)

    @staticmethod
    def _to_view(cart: ItemStock) -> RegisteredCartView:
        return RegisteredCartView(
            id=cart.id,
            container_code=cart.container_code,
            item_id=cart.item_id,
            location_id=cart.location_id,
            quantity=cart.quantity,
            is_locked=bool(cart.is_locked),
            locked_by_mission_code=cart.locked_by_mission_code,
            destination_location_id=cart.destination_location_id,
        )


class KukaFleetRackInserter(IFleetRackInserter):
    def __init__(self, fleet_client: KukaFleetClient):
        self._fleet_client = fleet_client

    def insert_rack(self, location_code: str, container_code: str) -> None:
        self._fleet_client.fleet_insert_rack(location_code, container_code)


class RegisterEventNotifier(IRegisterEventNotifier):
    def __init__(self, db: Session):
        self._db = db

    def notify_rack_registered(
        self, *, location_ids: List[int], container_code: str, operator_id: Optional[int]
    ) -> None:
        recipients = resolve_location_recipient_user_ids(
            self._db, location_ids, extra_user_ids=[operator_id]
        )
        publish_event(
            "floor.changed",
            {
                "reason": "rack_registered",
                "location_ids": location_ids,
                "container_code": container_code,
            },
            user_ids=recipients,
            admins=True,
        )
