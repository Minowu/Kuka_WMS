"""Core Production Operations (Raw material QR, Call CNC, Complete Stage, Return Empty Cart)."""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.modules.production.dispatch.cart_selector import CartSelector
from app.modules.production.dispatch.kuka_fleet_client import KukaFleetClient
from app.modules.production.dispatch.queue_service import QueueService
from app.modules.production.production_models import (
    FleetTask,
    Machine,
    ProductionRecord,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportQueue,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.socket.event_bus import publish_event, resolve_location_recipient_user_ids

logger = get_logger("main")


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
        """Assign stations/locations to an operator enforcing 1 user = 1 area."""
        unique_loc_ids = list(dict.fromkeys(location_ids))

        if unique_loc_ids:
            loc_objs = (
                db.query(Location)
                .filter(Location.id.in_(unique_loc_ids), Location.is_active.is_(True))
                .all()
            )
            if len(loc_objs) != len(unique_loc_ids):
                raise ValueError("Một hoặc nhiều vị trí (Location) không tồn tại hoặc đã bị khóa.")

            area_types = {loc.location_type for loc in loc_objs}
            if len(area_types) > 1:
                raise ValueError("Một tài khoản công nhân chỉ có thể được phân quyền trong 1 khu vực duy nhất.")

        db.query(UserLocation).filter(UserLocation.user_id == user_id).delete(synchronize_session=False)

        records = [
            UserLocation(user_id=user_id, location_id=loc_id)
            for loc_id in unique_loc_ids
        ]
        db.add_all(records)
        db.commit()
        return records

    def lock_cart_and_dispatch_fleet_task(
        self,
        db: Session,
        transport_req: TransportRequest,
        cart: ItemStock,
        pickup_location_id: int,
        dropoff_location_id: int,
    ) -> FleetTask:
        """Atomically lock container and create FleetTask (Tx1) then dispatch submitMission (Tx2)."""
        mission_code = f"MS{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"
        fleet_req_id = f"SUB{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}{uuid.uuid4().hex[:4].upper()}"

        cart.is_locked = True
        cart.locked_by_mission_code = mission_code
        cart.destination_location_id = dropoff_location_id

        transport_req.container_id = cart.id
        transport_req.source_location_id = pickup_location_id
        transport_req.destination_location_id = dropoff_location_id
        transport_req.status = "in_progress"

        fleet_task = FleetTask(
            mission_code=mission_code,
            fleet_request_id=fleet_req_id,
            transport_request_id=transport_req.id,
            pickup_location_id=pickup_location_id,
            dropoff_location_id=dropoff_location_id,
            container_id=cart.id,
            container_code=cart.container_code,
            status="pending_submit",
        )
        db.add(fleet_task)
        loc_ids = sorted({int(lid) for lid in (pickup_location_id, dropoff_location_id) if lid is not None})
        recipient_user_ids = resolve_location_recipient_user_ids(
            db,
            loc_ids,
            extra_user_ids=[transport_req.created_by],
        )
        db.commit()
        db.refresh(fleet_task)

        from app.modules.production.production_celery_task import enqueue_fleet_submit
        enqueue_fleet_submit(fleet_task.id)

        publish_event(
            "floor.changed",
            {
                "reason": "task_dispatched",
                "mission_code": mission_code,
                "location_ids": loc_ids,
            },
            user_ids=recipient_user_ids,
            admins=True,
        )

        return fleet_task

    def register_rack_at_raw_material(
        self,
        db: Session,
        location_id: int,
        item_id: int,
        container_code: str,
        quantity: Optional[int] = None,
        lot_number: Optional[str] = None,
        operator_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Register rack QR at Raw Material location and auto-dispatch waiting CNC requests."""
        clean_container_code = container_code.strip()
        if not clean_container_code:
            raise ValueError("Mã QR của rack (container_code) không được để trống.")

        location = db.query(Location).filter(Location.id == location_id, Location.is_active.is_(True)).first()
        if not location:
            raise ValueError(f"Vị trí cấp phôi (ID={location_id}) không tồn tại hoặc đã bị khóa.")
        if location.location_type != "RAW_MATERIAL":
            raise ValueError(f"Vị trí '{location.location_code}' không phải là vị trí Khu Nguyên Liệu (RAW_MATERIAL).")

        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise ValueError(f"Model sản phẩm ID={item_id} không tồn tại hoặc đã ngừng hoạt động.")

        occupying_cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.location_id == location.id,
                ItemStock.is_active.is_(True),
                ItemStock.container_code != clean_container_code,
            )
            .first()
        )
        if occupying_cart:
            raise ValueError(f"Vị trí '{location.location_code}' đang có xe/rack '{occupying_cart.container_code}' đỗ.")

        qty = quantity if (quantity is not None and quantity > 0) else (item.standard_quantity_per_cart or 120)

        cart = db.query(ItemStock).filter(ItemStock.container_code == clean_container_code).first()
        now = datetime.now(timezone.utc)
        if cart:
            if cart.is_locked:
                raise ValueError(f"Rack '{clean_container_code}' đang bị khóa bởi tác vụ vận chuyển '{cart.locked_by_mission_code}'.")
            if cart.is_active and cart.location_id and cart.location_id != location.id:
                curr_loc = db.query(Location).filter(Location.id == cart.location_id).first()
                loc_name = curr_loc.location_code if curr_loc else f"ID={cart.location_id}"
                raise ValueError(
                    f"Rack '{clean_container_code}' hiện đang hoạt động tại vị trí '{loc_name}'. "
                    f"Cần hoàn thành chu trình trước khi đăng ký lại ở Phôi Thô."
                )
            cart.item_id = item.id
            cart.location_id = location.id
            cart.destination_location_id = None
            cart.quantity = qty
            cart.current_stage_level = 0
            cart.status = "available"
            cart.is_active = True
            cart.is_locked = False
            cart.locked_by_mission_code = None
            cart.fleet_registered = True
            cart.created_at = now
        else:
            cart = ItemStock(
                container_code=clean_container_code,
                item_id=item.id,
                location_id=location.id,
                quantity=qty,
                current_stage_level=0,
                status="available",
                is_active=True,
                is_locked=False,
                fleet_registered=True,
                created_at=now,
            )
            db.add(cart)

        # Gọi KUKA Fleet để khai báo containerIn tại vị trí
        # Nếu Fleet từ chối, exception IcsError sẽ được ném ra -> rollback toàn bộ thay đổi DB
        try:
            self.fleet_client.fleet_insert_rack(location.location_code, clean_container_code)
        except Exception as e:
            db.rollback()
            logger.error("Khai báo xe phôi '%s' vào vị trí '%s' thất bại trên KUKA Fleet: %s", clean_container_code, location.location_code, e)
            raise ValueError(f"KUKA Fleet từ chối tiếp nhận xe phôi: {e}") from e

        db.flush()

        resolved = self.queue_service.try_resolve_waiting_cart_queue(
            db,
            stage_level=0,
            lock_and_dispatch_fn=self.lock_cart_and_dispatch_fleet_task,
        )
        loc_ids = sorted({int(lid) for lid in (location.id, cart.destination_location_id) if lid is not None})
        recipient_user_ids = resolve_location_recipient_user_ids(
            db,
            loc_ids,
            extra_user_ids=[operator_id],
        )
        db.commit()
        db.refresh(cart)

        publish_event(
            "floor.changed",
            {
                "reason": "rack_registered",
                "location_ids": loc_ids,
                "container_code": clean_container_code,
            },
            user_ids=recipient_user_ids,
            admins=True,
        )

        return {
            "success": True,
            "container_id": cart.id,
            "container_code": clean_container_code,
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

    def call_material_to_cnc(
        self,
        db: Session,
        destination_location_id: int,
        item_id: Optional[int] = None,
        required_stage_level: Optional[int] = None,
        created_by: Optional[int] = None,
        priority: int = 10,
    ) -> TransportRequest:
        """Operator at CNC station calls material (1-Touch pull)."""
        dest_loc = (
            db.query(Location)
            .filter(Location.id == destination_location_id, Location.is_active.is_(True))
            .first()
        )
        if not dest_loc:
            raise ValueError("Vị trí đích (Location) không tồn tại hoặc đã bị khóa.")

        if not self.selector.is_location_free(db, dest_loc.id):
            raise ValueError(
                f"Vị trí '{dest_loc.location_code}' hiện đang có xe hoặc đã có AMR đặt chỗ. Vui lòng chọn vị trí trống."
            )

        # ADR-002: Kiểm tra và xác thực item_id
        if item_id is None:
            raise ValueError(
                f"Vui lòng chọn Model sản phẩm cần gọi đến vị trí '{dest_loc.location_code}'."
            )

        # Xác thực máy này có được cấu hình gia công cho item_id trong ProductionRoute hay không
        input_lvl, _, _ = self.selector.get_stage_info_for_machine(db, dest_loc, item_id)
        if required_stage_level is None:
            required_stage_level = input_lvl

        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="CALL_CNC",
            item_id=item_id,
            destination_location_id=dest_loc.id,
            required_stage_level=required_stage_level,
            status="pending",
            priority=priority,
            created_by=created_by,
        )
        db.add(transport_req)
        db.flush()

        cart = self.selector.find_fifo_available_cart(
            db,
            item_id=item_id,
            stage_level=required_stage_level,
            target_location=dest_loc,
        )
        if cart:
            self.lock_cart_and_dispatch_fleet_task(
                db=db,
                transport_req=transport_req,
                cart=cart,
                pickup_location_id=cart.location_id,
                dropoff_location_id=dest_loc.id,
            )
        else:
            transport_req.status = "queued_for_cart"
            queue_entry = TransportQueue(
                request_id=transport_req.id,
                queue_type="WAITING_CART",
                target_stage_level=required_stage_level,
                status="PENDING",
                priority=priority,
            )
            db.add(queue_entry)

        loc_ids = sorted(
            {
                int(lid)
                for lid in (dest_loc.id, transport_req.source_location_id)
                if lid is not None
            }
        )
        recipient_user_ids = resolve_location_recipient_user_ids(
            db,
            loc_ids,
            extra_user_ids=[created_by],
        )
        db.commit()
        db.refresh(transport_req)

        if not cart:
            publish_event(
                "floor.changed",
                {
                    "reason": "call_material_queued",
                    "request_code": transport_req.request_code,
                    "location_ids": loc_ids,
                },
                user_ids=recipient_user_ids,
                admins=True,
            )

        return transport_req

    def complete_machining_stage(
        self,
        db: Session,
        container_code: Optional[str] = None,
        location_id: Optional[int] = None,
        operator_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Operator confirms completion of CNC machining stage on rack."""
        cart: Optional[ItemStock] = None
        if container_code:
            cart = (
                db.query(ItemStock)
                .filter(ItemStock.container_code == container_code.strip(), ItemStock.is_active.is_(True))
                .first()
            )
        elif location_id:
            cart = (
                db.query(ItemStock)
                .filter(ItemStock.location_id == location_id, ItemStock.is_active.is_(True))
                .first()
            )

        if not cart:
            target_desc = f"mã '{container_code}'" if container_code else f"vị trí ID={location_id}"
            raise ValueError(f"Không tìm thấy khay phôi (ItemStock) đang hoạt động tại {target_desc}.")

        if cart.is_locked:
            raise ValueError(f"Khay phôi '{cart.container_code}' đang bị khóa bởi nhiệm vụ '{cart.locked_by_mission_code}'.")

        loc = db.query(Location).filter(Location.id == cart.location_id).first()
        if not loc:
            raise ValueError(f"Vị trí của khay phôi '{cart.container_code}' không hợp lệ.")

        _, target_stage, is_final_cnc = self.selector.get_stage_info_for_machine(db, loc, cart.item_id)
        current_stage = cart.current_stage_level or 0

        # Kiểm tra ngăn chặn cập nhật vượt cấp: Nếu xe đã đạt hoặc vượt stage của máy này -> Chặn lại
        if current_stage >= target_stage:
            raise ValueError(
                f"Khay phôi '{cart.container_code}' đã hoàn thành công đoạn Level {current_stage} "
                f"của máy này (yêu cầu Level {target_stage}). Vui lòng chờ AMR vận chuyển sang công đoạn tiếp theo."
            )

        completed_stage = target_stage
        previous_stage = cart.current_stage_level
        cart.current_stage_level = completed_stage

        machine_code = loc.machine.machine_code if loc.machine else None
        record = ProductionRecord(
            container_id=cart.id,
            container_code=cart.container_code,
            item_id=cart.item_id,
            stage_level=completed_stage,
            location_id=cart.location_id,
            machine_code=machine_code,
            operator_id=operator_id,
            notes=notes,
        )
        db.add(record)

        if not is_final_cnc:
            recipient_user_ids = resolve_location_recipient_user_ids(
                db,
                [loc.id],
                extra_user_ids=[operator_id],
            )
            db.commit()
            self.queue_service.try_resolve_waiting_cart_queue(
                db,
                stage_level=completed_stage,
                lock_and_dispatch_fn=self.lock_cart_and_dispatch_fleet_task,
            )
            publish_event(
                "floor.changed",
                {
                    "reason": "stage_completed",
                    "location_ids": [loc.id],
                    "container_code": cart.container_code,
                },
                user_ids=recipient_user_ids,
                admins=True,
            )
            return {
                "container_code": cart.container_code,
                "completed_stage_level": completed_stage,
                "is_final_cnc_step": False,
                "action": "WIP_AVAILABLE_FOR_NEXT_STAGE",
            }

        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        wash_slot = self.selector.find_available_slot_to_wash(db)
        if wash_slot:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="MOVE_TO_WASH",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=wash_slot.id,
                container_id=cart.id,
                required_stage_level=completed_stage,
                status="pending",
                priority=5,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            try:
                self.lock_cart_and_dispatch_fleet_task(
                    db=db,
                    transport_req=transport_req,
                    cart=cart,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=wash_slot.id,
                )
            except Exception as e:
                # Nếu gửi lệnh sang KUKA Fleet thất bại, khôi phục lại stage_level ban đầu
                # để nút 'Báo xong' trên PDA không bị ẩn mất vĩnh viễn!
                cart.current_stage_level = previous_stage
                db.commit()
                raise
            action_result = "DISPATCHED_TO_WASHING"
        else:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="MOVE_TO_WASH",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=cart.location_id,
                container_id=cart.id,
                required_stage_level=completed_stage,
                status="queued_for_slot",
                priority=5,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            queue_entry = TransportQueue(
                request_id=transport_req.id,
                queue_type="WAITING_SLOT",
                target_stage_level=99,
                status="PENDING",
                priority=5,
            )
            db.add(queue_entry)
            action_result = "QUEUED_FOR_WASHING_SLOT"

        loc_ids = sorted(
            {
                int(lid)
                for lid in (loc.id, wash_slot.id if wash_slot else None)
                if lid is not None
            }
        )
        recipient_user_ids = resolve_location_recipient_user_ids(
            db,
            loc_ids,
            extra_user_ids=[operator_id],
        )
        db.commit()

        if not wash_slot:
            publish_event(
                "floor.changed",
                {
                    "reason": "stage_completed_queued_wash",
                    "location_ids": loc_ids,
                    "container_code": cart.container_code,
                },
                user_ids=recipient_user_ids,
                admins=True,
            )

        return {
            "container_code": cart.container_code,
            "completed_stage_level": completed_stage,
            "is_final_cnc_step": True,
            "action": action_result,
            "request_code": transport_req.request_code,
        }

    def complete_washing_and_return_empty_cart(
        self,
        db: Session,
        container_code: str,
        operator_id: Optional[int] = None,
    ) -> TransportRequest:
        """Empty cart return from Washing Station to EMPTY_CART_BUFFER."""
        clean_code = container_code.strip()
        cart = (
            db.query(ItemStock)
            .filter(ItemStock.container_code == clean_code, ItemStock.is_active.is_(True))
            .first()
        )
        if not cart:
            raise ValueError(f"Không tìm thấy khay/xe '{clean_code}' đang hoạt động tại khu Tẩy rửa.")

        if cart.is_locked:
            raise ValueError(f"Xe '{clean_code}' đang bị khóa bởi nhiệm vụ '{cart.locked_by_mission_code}'.")

        loc = db.query(Location).filter(Location.id == cart.location_id).first()
        if not loc or loc.location_type != "WASHING_SLOT":
            raise ValueError(f"Xe '{clean_code}' không nằm tại vị trí Khu Tẩy Rửa (WASHING_SLOT).")

        buffer_slot = self.selector.find_next_empty_buffer_slot(db)
        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"

        if buffer_slot:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="RETURN_EMPTY_CART",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=buffer_slot.id,
                container_id=cart.id,
                required_stage_level=0,
                status="pending",
                priority=15,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            cart.quantity = 0
            cart.status = "empty"
            cart.current_stage_level = 0
            db.flush()

            try:
                self.lock_cart_and_dispatch_fleet_task(
                    db=db,
                    transport_req=transport_req,
                    cart=cart,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=buffer_slot.id,
                )
            except Exception:
                cart.status = "available"
                db.commit()
                raise
        else:
            cart.quantity = 0
            cart.status = "empty"
            cart.current_stage_level = 0
            db.flush()
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="RETURN_EMPTY_CART",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=cart.location_id,
                container_id=cart.id,
                required_stage_level=0,
                status="queued_for_slot",
                priority=15,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            db.add(
                TransportQueue(
                    request_id=transport_req.id,
                    queue_type="WAITING_SLOT",
                    target_stage_level=0,
                    status="PENDING",
                    priority=15,
                )
            )

        loc_ids = sorted(
            {
                int(lid)
                for lid in (loc.id, buffer_slot.id if buffer_slot else None)
                if lid is not None
            }
        )
        recipient_user_ids = resolve_location_recipient_user_ids(
            db,
            loc_ids,
            extra_user_ids=[operator_id],
        )
        db.commit()

        if not buffer_slot:
            publish_event(
                "floor.changed",
                {
                    "reason": "washing_released_queued",
                    "location_ids": loc_ids,
                    "container_code": clean_code,
                },
                user_ids=recipient_user_ids,
                admins=True,
            )

        self.queue_service.try_resolve_waiting_slot_queue(
            db,
            lock_and_dispatch_fn=self.lock_cart_and_dispatch_fleet_task,
        )

        db.refresh(transport_req)
        return transport_req
