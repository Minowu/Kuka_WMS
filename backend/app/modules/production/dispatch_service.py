"""
Production & AMR Dispatch Engine Service.

Implements:
1. User Location Assignment Constraint (Max 3 CNC stations per user).
2. Raw Material Rack QR Registration (reusable physical rack `cart_code` -> Fleet POST insert + ItemStock upsert + auto-resolve WAITING_CART queue).
3. FIFO Cart Selection (`created_at ASC` with `FOR UPDATE SKIP LOCKED` anti-race-condition).
4. POS1 / POS2 CNC Slot Allocation (normalized 3NF via `Machine` & `RouteStepMachine`) & Waiting Queue Management (`TransportQueue`).
5. Stage Progression (`complete_machining_stage`: Level 0 -> Level 1 -> Level 2 -> Level 3 -> Washing -> Empty Cart Return).
6. KUKA Fleet Manager (RCS/ICS) HTTP Adapter (`add_task`, `create_fleet_task`, and 6 Fleet command hooks) & Webhook Callback (`receive_task_status` -> `TaskStatus` + `FleetTask` + `ItemStock` settlement).
"""

from datetime import datetime, timezone
import json
from typing import Any, Optional
import uuid

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.logger import get_logger
from app.modules.production.production_models import (
    MAPPING_STATUS,
    FleetTask,
    Machine,
    ProductionRecord,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TaskStatus,
    TransportQueue,
    TransportRequest,
    UserLocation,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("main")

MAX_LOCATIONS_PER_USER = 3


def _ics_configured() -> bool:
    base = (settings.ics_base_url or "").strip()
    return bool(base and base != "Your RCS Server path" and base.startswith("http"))


class IcsError(Exception):
    """Exception raised when communicating with KUKA Fleet Manager (ICS/RCS)."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class DispatchService:
    """Core service for CNC work-in-progress (WIP) cart routing and KUKA AMR fleet dispatch."""

    # =========================================================================
    # 0. KUKA FLEET MANAGER (RCS / ICS) HTTP ADAPTER & COMMAND HOOKS
    # =========================================================================

    def add_task(self, payload: dict[str, Any], endpoint_path: str = "/ics/taskOrder/addTask") -> dict[str, Any]:
        """
        Send a low-level HTTP POST request to KUKA Fleet Manager (RCS/ICS).
        When running locally without a live RCS server configured, returns a simulated success response.
        """
        if not _ics_configured():
            logger.info("ICS offline/dev mode — simulated POST %s payload=%s", endpoint_path, payload)
            return {"code": 1000, "simulated": True, "payload": payload}

        url = f"{settings.ics_base_url.rstrip('/')}:7000{endpoint_path}"
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0)) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            logger.info("ICS POST %s response: %s", endpoint_path, data)
            return data
        except httpx.HTTPStatusError as e:
            retryable = e.response.status_code >= 500
            raise IcsError(f"ICS server error ({e.response.status_code})", retryable=retryable) from e
        except httpx.RequestError as e:
            raise IcsError("Cannot reach ICS server", retryable=True) from e

    def fleet_insert_rack(self, location_code: str, cart_code: str) -> dict[str, Any]:
        """
        [FLEET COMMAND 1 - POST INSERT RACK]
        Bind/insert physical rack QR (`cart_code`) into `location_code` on KUKA Fleet Manager
        so Fleet knows a rack is present at that node before dispatching an AMR to pick it up.
        (Exact endpoint/payload will be plugged in when provided.)
        """
        payload = {
            "action": "INSERT_RACK",
            "locationCode": location_code,
            "shelfNumber": cart_code,
            "qrCode": cart_code,
            "fromSystem": "MES",
        }
        logger.info("Fleet insert rack: cart_code=%s at location_code=%s", cart_code, location_code)
        return self.add_task(payload, endpoint_path="/ics/shelf/insert")

    def fleet_move_material(
        self,
        task: FleetTask,
        pickup_code: str,
        dropoff_code: str,
        cart_code: Optional[str],
    ) -> dict[str, Any]:
        """
        [FLEET COMMAND 2 - POST MOVE MATERIAL]
        Dispatch AMR to move a loaded rack (`cart_code`) from Raw Material -> CNC or CNC Level N -> CNC Level N+1.
        """
        detail = [
            {
                "taskPath": f"{pickup_code},{dropoff_code}",
                "shelfNumber": cart_code or "",
            }
        ]
        task.process_code = task.process_code or "move_material"
        task.system_code = task.system_code or "MES"
        task.task_order_detail = json.dumps(detail, ensure_ascii=False)
        payload = {
            "orderId": task.task_code,
            "modelProcessCode": task.process_code,
            "fromSystem": task.system_code,
            "taskOrderDetail": detail,
        }
        return self.add_task(payload)

    def fleet_move_to_wash(
        self,
        task: FleetTask,
        pickup_code: str,
        wash_code: str,
        cart_code: Optional[str],
    ) -> dict[str, Any]:
        """
        [FLEET COMMAND 3 - POST MOVE TO WASH]
        Dispatch AMR to move a finished CNC rack (`cart_code`) from final CNC step to Washing station.
        """
        detail = [
            {
                "taskPath": f"{pickup_code},{wash_code}",
                "shelfNumber": cart_code or "",
            }
        ]
        task.process_code = task.process_code or "move_to_wash"
        task.system_code = task.system_code or "MES"
        task.task_order_detail = json.dumps(detail, ensure_ascii=False)
        payload = {
            "orderId": task.task_code,
            "modelProcessCode": task.process_code,
            "fromSystem": task.system_code,
            "taskOrderDetail": detail,
        }
        return self.add_task(payload)

    def fleet_move_empty_rack(
        self,
        task: FleetTask,
        pickup_code: str,
        buffer_code: str,
        cart_code: Optional[str],
    ) -> dict[str, Any]:
        """
        [FLEET COMMAND 4 - POST MOVE EMPTY RACK]
        Dispatch AMR to return an empty rack (`cart_code`) from CNC/Washing to Empty Cart Buffer.
        """
        detail = [
            {
                "taskPath": f"{pickup_code},{buffer_code}",
                "shelfNumber": cart_code or "",
            }
        ]
        task.process_code = task.process_code or "move_empty_rack"
        task.system_code = task.system_code or "MES"
        task.task_order_detail = json.dumps(detail, ensure_ascii=False)
        payload = {
            "orderId": task.task_code,
            "modelProcessCode": task.process_code,
            "fromSystem": task.system_code,
            "taskOrderDetail": detail,
        }
        return self.add_task(payload)

    def fleet_remove_rack(self, location_code: str, cart_code: str) -> dict[str, Any]:
        """
        [FLEET COMMAND 5 - POST REMOVE/UNBIND RACK]
        Clear rack binding on Fleet Manager when a rack is manually removed from a location.
        """
        payload = {
            "action": "REMOVE_RACK",
            "locationCode": location_code,
            "shelfNumber": cart_code,
            "fromSystem": "MES",
        }
        return self.add_task(payload, endpoint_path="/ics/shelf/remove")

    def fleet_cancel_task(self, task_code: str) -> dict[str, Any]:
        """
        [FLEET COMMAND 6 - POST CANCEL TASK]
        Cancel an active Fleet task by `orderId` (`task_code`).
        """
        payload = {
            "orderId": task_code,
            "fromSystem": "MES",
        }
        return self.add_task(payload, endpoint_path="/ics/taskOrder/cancelTask")

    def create_fleet_task(self, db: Session, task: FleetTask, request_type: str = "CALL_MATERIAL") -> FleetTask:
        """
        Send the appropriate POST command to KUKA Fleet Manager for a `FleetTask` and persist it.
        Replaces legacy `TaskStatusService.create_robot_task`.
        """
        pickup_loc = db.query(Location).filter(Location.id == task.pickup_location_id).first()
        dropoff_loc = db.query(Location).filter(Location.id == task.dropoff_location_id).first()
        cart = db.query(ItemStock).filter(ItemStock.id == task.cart_id).first() if task.cart_id else None

        pickup_code = pickup_loc.location_code if pickup_loc else str(task.pickup_location_id)
        dropoff_code = dropoff_loc.location_code if dropoff_loc else str(task.dropoff_location_id)
        cart_code = cart.cart_code if cart else None

        if request_type == "MOVE_TO_WASH":
            self.fleet_move_to_wash(task, pickup_code, dropoff_code, cart_code)
        elif request_type == "RETURN_EMPTY_CART":
            self.fleet_move_empty_rack(task, pickup_code, dropoff_code, cart_code)
        else:
            self.fleet_move_material(task, pickup_code, dropoff_code, cart_code)

        task.status = "sent"
        task.sent_at = datetime.now(timezone.utc)
        db.add(task)
        db.flush()
        return task

    # =========================================================================
    # 1. USER LOCATION ASSIGNMENT (MAX 3 LOCATIONS PER USER)
    # =========================================================================

    def assign_locations_to_user(
        self,
        db: Session,
        user_id: int,
        location_ids: list[int],
    ) -> list[UserLocation]:
        """
        Assign up to 3 CNC stations/locations to an operator.
        Raises ValueError if more than 3 locations are provided.
        """
        unique_loc_ids = list(dict.fromkeys(location_ids))
        if len(unique_loc_ids) > MAX_LOCATIONS_PER_USER:
            raise ValueError(
                f"Mỗi tài khoản vận hành chỉ được phép gắn tối đa {MAX_LOCATIONS_PER_USER} vị trí làm việc."
            )

        if unique_loc_ids:
            valid_count = (
                db.query(Location)
                .filter(Location.id.in_(unique_loc_ids), Location.is_active.is_(True))
                .count()
            )
            if valid_count != len(unique_loc_ids):
                raise ValueError("Một hoặc nhiều vị trí (Location) không tồn tại hoặc đã bị khóa.")

        db.query(UserLocation).filter(UserLocation.user_id == user_id).delete(synchronize_session=False)

        records = [
            UserLocation(user_id=user_id, location_id=loc_id)
            for loc_id in unique_loc_ids
        ]
        db.add_all(records)
        db.commit()
        return records

    # =========================================================================
    # 2. RAW MATERIAL RACK QR REGISTRATION (REUSABLE RACK QR -> FLEET INSERT + AUTO DISPATCH)
    # =========================================================================

    def register_rack_at_raw_material(
        self,
        db: Session,
        location_id: int,
        item_id: int,
        cart_code: str,
        quantity: Optional[int] = None,
        lot_number: Optional[str] = None,
        operator_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        When a worker at the Raw Material zone:
        1. Selects a Raw Material location (`location_id`)
        2. Selects a Product Model (`item_id`)
        3. Scans the reusable physical Rack QR (`cart_code`)

        This method:
        - Validates that the location is free.
        - Sends `fleet_insert_rack` POST to KUKA Fleet Manager so Fleet binds the rack at that node.
        - Creates or reuses the `ItemStock` row for `cart_code` with `current_stage_level = 0`, `is_locked = False`.
        - Immediately calls `try_resolve_waiting_cart_queue(db, stage_level=0)` so if a CNC machine is
          already waiting in `TransportQueue` (`WAITING_CART`) for that model, an AMR is dispatched right away!
        """
        clean_cart_code = cart_code.strip()
        if not clean_cart_code:
            raise ValueError("Mã QR của rack (cart_code) không được để trống.")

        location = (
            db.query(Location)
            .filter(Location.id == location_id, Location.is_active.is_(True))
            .first()
        )
        if not location:
            raise ValueError(f"Vị trí ID={location_id} không tồn tại hoặc đã ngừng hoạt động.")

        item = (
            db.query(Item)
            .filter(Item.id == item_id, Item.is_active.is_(True))
            .first()
        )
        if not item:
            raise ValueError(f"Model sản phẩm ID={item_id} không tồn tại hoặc đã ngừng hoạt động.")

        # Check if another active cart is already occupying this location
        occupying_cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.location_id == location.id,
                ItemStock.is_active.is_(True),
                ItemStock.cart_code != clean_cart_code,
            )
            .first()
        )
        if occupying_cart:
            raise ValueError(
                f"Vị trí '{location.location_code}' đang có xe/rack '{occupying_cart.cart_code}' đỗ."
            )

        qty = quantity if (quantity is not None and quantity > 0) else (item.standard_quantity_per_cart or 120)

        # 1. Notify KUKA Fleet Manager to insert/bind the rack at this location
        self.fleet_insert_rack(location.location_code, clean_cart_code)

        # 2. Reuse existing ItemStock row if rack QR was used in a previous cycle, or create new
        cart = db.query(ItemStock).filter(ItemStock.cart_code == clean_cart_code).first()
        now = datetime.now(timezone.utc)
        if cart:
            if cart.is_locked:
                raise ValueError(
                    f"Rack '{clean_cart_code}' đang bị khóa bởi tác vụ vận chuyển '{cart.locked_by_task_id}'."
                )
            cart.item_id = item.id
            cart.location_id = location.id
            cart.destination_location_id = None
            cart.quantity = qty
            cart.current_stage_level = 0
            cart.status = "available"
            cart.is_active = True
            cart.is_locked = False
            cart.locked_by_task_id = None
            cart.created_at = now
        else:
            cart = ItemStock(
                cart_code=clean_cart_code,
                item_id=item.id,
                location_id=location.id,
                destination_location_id=None,
                quantity=qty,
                current_stage_level=0,
                status="available",
                is_active=True,
                is_locked=False,
                locked_by_task_id=None,
            )
            db.add(cart)

        db.commit()
        db.refresh(cart)

        # 3. Check if any CNC station is waiting in TransportQueue (WAITING_CART) for Level 0
        resolved_count = self.try_resolve_waiting_cart_queue(db, stage_level=0)
        db.refresh(cart)

        return {
            "cart_id": cart.id,
            "cart_code": cart.cart_code,
            "item_id": item.id,
            "sku": item.sku,
            "location_id": location.id,
            "location_code": location.location_code,
            "quantity": int(cart.quantity),
            "current_stage_level": cart.current_stage_level,
            "is_locked": cart.is_locked,
            "fleet_inserted": True,
            "resolved_queue_count": resolved_count,
            "dispatched_task_code": cart.locked_by_task_id,
        }

    # =========================================================================
    # 3. FIFO CART SELECTION & SLOT ALLOCATION HELPERS
    # =========================================================================

    def find_fifo_available_cart(
        self,
        db: Session,
        item_id: int,
        stage_level: int = 0,
    ) -> Optional[ItemStock]:
        """
        Select the oldest available cart (FIFO: `created_at ASC, id ASC`) matching
        `item_id` and `current_stage_level`.
        Uses `with_for_update(skip_locked=True)` so concurrent requests never pick the same cart.
        """
        location_types = ["RAW_MATERIAL"] if stage_level == 0 else ["CNC_SLOT", "RAW_MATERIAL"]

        cart = (
            db.query(ItemStock)
            .join(Location, ItemStock.location_id == Location.id)
            .filter(
                ItemStock.item_id == item_id,
                ItemStock.current_stage_level == stage_level,
                ItemStock.is_locked.is_(False),
                ItemStock.is_active.is_(True),
                ItemStock.quantity > 0,
                Location.location_type.in_(location_types),
                Location.is_active.is_(True),
            )
            .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
            .with_for_update(of=ItemStock, skip_locked=True)
            .first()
        )
        return cart

    def _is_location_free(self, db: Session, location_id: int) -> bool:
        """
        A location is free if:
        1. No active cart is currently sitting at `location_id`.
        2. No locked cart is currently in-transit heading to `destination_location_id == location_id`.
        3. No active FleetTask has `dropoff_location_id == location_id`.
        """
        occupied_by_cart = (
            db.query(ItemStock.id)
            .filter(
                ItemStock.location_id == location_id,
                ItemStock.is_active.is_(True),
            )
            .first()
        )
        if occupied_by_cart:
            return False

        reserved_by_cart = (
            db.query(ItemStock.id)
            .filter(
                ItemStock.destination_location_id == location_id,
                ItemStock.is_locked.is_(True),
                ItemStock.is_active.is_(True),
            )
            .first()
        )
        if reserved_by_cart:
            return False

        reserved_by_task = (
            db.query(FleetTask.id)
            .filter(
                FleetTask.dropoff_location_id == location_id,
                FleetTask.status.in_(["created", "sent", "in_progress"]),
            )
            .first()
        )
        if reserved_by_task:
            return False

        return True

    def find_available_slot_for_machines(
        self,
        db: Session,
        allowed_machines: list[str],
        allowed_machine_ids: Optional[list[int]] = None,
    ) -> Optional[Location]:
        """
        Find a free CNC slot among `allowed_machines` (normalized 3NF via `machine_id` or `machine_code`).
        Prioritizes `position_index == 1` (POS1 working slot) before `position_index == 2` (POS2 buffer slot).
        """
        if not allowed_machines and not allowed_machine_ids:
            return None

        machine_filters = []
        if allowed_machine_ids:
            machine_filters.append(Location.machine_id.in_(allowed_machine_ids))
        if allowed_machines:
            machine_filters.append(Location.machine_code.in_(allowed_machines))

        candidate_slots = (
            db.query(Location)
            .filter(
                Location.location_type == "CNC_SLOT",
                or_(*machine_filters),
                Location.is_active.is_(True),
            )
            .order_by(Location.position_index.asc(), Location.id.asc())
            .all()
        )

        for slot in candidate_slots:
            if self._is_location_free(db, slot.id):
                return slot

        return None

    def find_available_slot_by_type(
        self,
        db: Session,
        location_type: str,
    ) -> Optional[Location]:
        """Find any free location of a given `location_type` (e.g. WASHING_SLOT, EMPTY_CART_BUFFER)."""
        candidate_slots = (
            db.query(Location)
            .filter(
                Location.location_type == location_type,
                Location.is_active.is_(True),
            )
            .order_by(Location.position_index.asc().nullsfirst(), Location.id.asc())
            .all()
        )
        for slot in candidate_slots:
            if self._is_location_free(db, slot.id):
                return slot
        return None

    # =========================================================================
    # 4. CALL MATERIAL TO CNC STATION (SCENARIO 1 & 2: BUFFERING / QUEUEING)
    # =========================================================================

    def call_material_to_cnc(
        self,
        db: Session,
        destination_location_id: int,
        item_id: int,
        required_stage_level: int = 0,
        created_by: Optional[int] = None,
        priority: int = 10,
    ) -> TransportRequest:
        """
        Operator at a CNC station requests a cart of `item_id` (default `stage_level = 0` raw material).
        - If the requested `destination_location_id` (e.g. POS1) is occupied, automatically checks if the
          sibling slot (POS2) of the same CNC machine is free and routes there.
        - If a matching cart is available in FIFO order, locks the cart and creates a `FleetTask`.
        - If no cart is available yet, places the request into `TransportQueue` (`WAITING_CART`).
        """
        dest_loc = (
            db.query(Location)
            .filter(Location.id == destination_location_id, Location.is_active.is_(True))
            .first()
        )
        if not dest_loc:
            raise ValueError("Vị trí đích (Location) không tồn tại hoặc đã bị khóa.")

        # Check if target slot is free; if occupied and part of a dual-slot CNC machine, fallback to POS2
        if not self._is_location_free(db, dest_loc.id):
            if dest_loc.machine_id or dest_loc.machine_code:
                sibling_query = db.query(Location).filter(
                    Location.id != dest_loc.id,
                    Location.location_type == "CNC_SLOT",
                    Location.is_active.is_(True),
                )
                if dest_loc.machine_id:
                    sibling_query = sibling_query.filter(Location.machine_id == dest_loc.machine_id)
                else:
                    sibling_query = sibling_query.filter(Location.machine_code == dest_loc.machine_code)

                sibling_slots = sibling_query.order_by(Location.position_index.asc()).all()
                free_sibling = next((s for s in sibling_slots if self._is_location_free(db, s.id)), None)
                if free_sibling:
                    dest_loc = free_sibling
                else:
                    raise ValueError(
                        f"Cả 2 vị trí của máy {dest_loc.machine_code} đều đang đầy hoặc đang có xe tiến vào."
                    )
            else:
                raise ValueError(f"Vị trí {dest_loc.location_code} hiện đang có xe hoặc đã được đặt chỗ.")

        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        transport_req = TransportRequest(
            request_code=req_code,
            request_type="CALL_MATERIAL",
            item_id=item_id,
            destination_location_id=dest_loc.id,
            required_stage_level=required_stage_level,
            status="pending",
            priority=priority,
            created_by=created_by,
        )
        db.add(transport_req)
        db.flush()

        # Find FIFO cart
        cart = self.find_fifo_available_cart(db, item_id=item_id, stage_level=required_stage_level)
        if cart:
            self._lock_cart_and_dispatch_fleet_task(
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

        db.commit()
        db.refresh(transport_req)
        return transport_req

    # =========================================================================
    # 5. COMPLETE MACHINING STAGE & AUTO-ROUTE NEXT STEP / WASHING
    # =========================================================================

    def complete_machining_stage(
        self,
        db: Session,
        cart_code: str,
        operator_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Called when an operator finishes machining a cart at a CNC station:
        1. Increments `cart.current_stage_level` (e.g., 0 -> 1, 1 -> 2, 2 -> 3).
        2. Records a `ProductionRecord` audit entry.
        3. Looks up the active `ProductionRoute` for `cart.item_id`:
           - If a next `RouteStep` exists (`stage_level == cart.current_stage_level + 1`):
             Finds an available slot (POS1/POS2) among normalized `RouteStepMachine` machines.
             If a slot is free -> immediately dispatches AMR (`MOVE_NEXT_STAGE`).
             If all slots are full -> enqueues into `TransportQueue` (`WAITING_SLOT`).
           - If the current step was the final CNC step (`is_final_cnc_step=True` or no next step):
             Routes the cart to an available `WASHING_SLOT` (`MOVE_TO_WASH`), or enqueues if full.
        """
        cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.cart_code == cart_code.strip(),
                ItemStock.is_active.is_(True),
            )
            .with_for_update()
            .first()
        )
        if not cart:
            raise ValueError(f"Không tìm thấy xe hàng (cart_code='{cart_code}').")
        if cart.is_locked:
            raise ValueError(f"Xe hàng '{cart_code}' đang bị khóa bởi tác vụ vận chuyển khác.")
        if not cart.location_id:
            raise ValueError(f"Xe hàng '{cart_code}' chưa có vị trí hiện tại.")

        current_loc = db.query(Location).filter(Location.id == cart.location_id).first()

        # Advance stage level: if cart arrived as raw material (0), finishing the first CNC machine brings it to 1
        completed_stage = (cart.current_stage_level or 0) + 1
        cart.current_stage_level = completed_stage

        prod_record = ProductionRecord(
            cart_code=cart.cart_code,
            cart_id=cart.id,
            item_id=cart.item_id,
            machine_code=current_loc.machine_code if current_loc else None,
            location_id=cart.location_id,
            stage_level=completed_stage,
            operator_id=operator_id,
            notes=notes,
        )
        db.add(prod_record)
        db.flush()

        # Lookup active production route for this item
        route = (
            db.query(ProductionRoute)
            .filter(
                ProductionRoute.item_id == cart.item_id,
                ProductionRoute.is_active.is_(True),
            )
            .first()
        )

        next_stage_level = completed_stage + 1
        next_step: Optional[RouteStep] = None
        current_step: Optional[RouteStep] = None

        if route:
            current_step = (
                db.query(RouteStep)
                .filter(
                    RouteStep.route_id == route.id,
                    RouteStep.stage_level == completed_stage,
                )
                .first()
            )
            if not (current_step and current_step.is_final_cnc_step):
                next_step = (
                    db.query(RouteStep)
                    .options(
                        joinedload(RouteStep.allowed_machine_links).joinedload(RouteStepMachine.machine)
                    )
                    .filter(
                        RouteStep.route_id == route.id,
                        RouteStep.stage_level == next_stage_level,
                    )
                    .first()
                )

        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"

        if next_step:
            allowed_machines = next_step.allowed_machines
            allowed_machine_ids = [
                link.machine_id for link in (next_step.allowed_machine_links or []) if link.machine_id
            ]
            target_slot = self.find_available_slot_for_machines(
                db,
                allowed_machines,
                allowed_machine_ids=allowed_machine_ids,
            )

            if target_slot:
                transport_req = TransportRequest(
                    request_code=req_code,
                    request_type="MOVE_NEXT_STAGE",
                    item_id=cart.item_id,
                    source_location_id=cart.location_id,
                    destination_location_id=target_slot.id,
                    cart_id=cart.id,
                    required_stage_level=completed_stage,
                    status="pending",
                    priority=5,
                    created_by=operator_id,
                )
                db.add(transport_req)
                db.flush()

                self._lock_cart_and_dispatch_fleet_task(
                    db=db,
                    transport_req=transport_req,
                    cart=cart,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=target_slot.id,
                )
                action_result = "DISPATCHED_TO_NEXT_STAGE"
            else:
                # All slots for next stage are currently occupied -> enqueue in WAITING_SLOT
                transport_req = TransportRequest(
                    request_code=req_code,
                    request_type="MOVE_NEXT_STAGE",
                    item_id=cart.item_id,
                    source_location_id=cart.location_id,
                    destination_location_id=cart.location_id,  # Temporary placeholder until slot frees up
                    cart_id=cart.id,
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
                    target_stage_level=next_stage_level,
                    status="PENDING",
                    priority=5,
                )
                db.add(queue_entry)
                action_result = "QUEUED_FOR_NEXT_STAGE_SLOT"
        else:
            # Final CNC stage completed -> Route to WASHING_SLOT
            wash_slot = self.find_available_slot_by_type(db, "WASHING_SLOT")
            if wash_slot:
                transport_req = TransportRequest(
                    request_code=req_code,
                    request_type="MOVE_TO_WASH",
                    item_id=cart.item_id,
                    source_location_id=cart.location_id,
                    destination_location_id=wash_slot.id,
                    cart_id=cart.id,
                    required_stage_level=completed_stage,
                    status="pending",
                    priority=5,
                    created_by=operator_id,
                )
                db.add(transport_req)
                db.flush()

                self._lock_cart_and_dispatch_fleet_task(
                    db=db,
                    transport_req=transport_req,
                    cart=cart,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=wash_slot.id,
                )
                action_result = "DISPATCHED_TO_WASHING"
            else:
                transport_req = TransportRequest(
                    request_code=req_code,
                    request_type="MOVE_TO_WASH",
                    item_id=cart.item_id,
                    source_location_id=cart.location_id,
                    destination_location_id=cart.location_id,
                    cart_id=cart.id,
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
                    target_stage_level=99,  # 99 denotes WASHING_SLOT
                    status="PENDING",
                    priority=5,
                )
                db.add(queue_entry)
                action_result = "QUEUED_FOR_WASHING_SLOT"

        db.commit()
        return {
            "cart_code": cart.cart_code,
            "completed_stage_level": completed_stage,
            "action": action_result,
            "request_code": transport_req.request_code,
        }

    # =========================================================================
    # 6. EMPTY CART RETURN & WASHING COMPLETION (SCENARIO 3 & 4)
    # =========================================================================

    def release_empty_cart_from_cnc(
        self,
        db: Session,
        cart_code: str,
        operator_id: Optional[int] = None,
    ) -> TransportRequest:
        """
        Scenario 3 (Trả xe rỗng tại CNC):
        When workpieces are transferred onto another cart at a CNC station and the source cart becomes empty,
        reset its quantity to 0 and dispatch an AMR to return it to `EMPTY_CART_BUFFER`.
        """
        cart = (
            db.query(ItemStock)
            .filter(ItemStock.cart_code == cart_code.strip(), ItemStock.is_active.is_(True))
            .with_for_update()
            .first()
        )
        if not cart or not cart.location_id:
            raise ValueError(f"Không tìm thấy xe '{cart_code}' tại vị trí hợp lệ.")
        if cart.is_locked:
            raise ValueError(f"Xe '{cart_code}' đang bị khóa bởi lệnh vận chuyển khác.")

        cart.quantity = 0
        cart.current_stage_level = 0
        cart.status = "empty"

        empty_buffer = self.find_available_slot_by_type(db, "EMPTY_CART_BUFFER")
        req_code = f"REQ-{uuid.uuid4().hex[:8].upper()}"

        if empty_buffer:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="RETURN_EMPTY_CART",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=empty_buffer.id,
                cart_id=cart.id,
                required_stage_level=0,
                status="pending",
                priority=15,
                created_by=operator_id,
            )
            db.add(transport_req)
            db.flush()

            self._lock_cart_and_dispatch_fleet_task(
                db=db,
                transport_req=transport_req,
                cart=cart,
                pickup_location_id=cart.location_id,
                dropoff_location_id=empty_buffer.id,
            )
        else:
            transport_req = TransportRequest(
                request_code=req_code,
                request_type="RETURN_EMPTY_CART",
                item_id=cart.item_id,
                source_location_id=cart.location_id,
                destination_location_id=cart.location_id,
                cart_id=cart.id,
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

        db.commit()
        db.refresh(transport_req)
        return transport_req

    def complete_washing_and_return_empty_cart(
        self,
        db: Session,
        cart_code: str,
        operator_id: Optional[int] = None,
    ) -> TransportRequest:
        """
        Scenario 4 (Hoàn thành Tẩy rửa -> Trả xe rỗng):
        Operator at the washing station confirms washing is complete; finished goods are unloaded,
        cart is marked empty (`quantity = 0`), and AMR returns the empty cart to `EMPTY_CART_BUFFER`.
        """
        return self.release_empty_cart_from_cnc(db=db, cart_code=cart_code, operator_id=operator_id)

    # =========================================================================
    # 7. FLEET TASK EXECUTION, WEBHOOK CALLBACKS & QUEUE RESOLUTION
    # =========================================================================

    def _lock_cart_and_dispatch_fleet_task(
        self,
        db: Session,
        transport_req: TransportRequest,
        cart: ItemStock,
        pickup_location_id: int,
        dropoff_location_id: int,
    ) -> FleetTask:
        """Atomically lock the cart, set its destination, create a `FleetTask`, and call Fleet Manager."""
        task_code = f"TASK-{uuid.uuid4().hex[:8].upper()}"

        cart.is_locked = True
        cart.locked_by_task_id = task_code
        cart.destination_location_id = dropoff_location_id

        transport_req.cart_id = cart.id
        transport_req.source_location_id = pickup_location_id
        transport_req.destination_location_id = dropoff_location_id
        transport_req.status = "in_progress"

        fleet_task = FleetTask(
            task_code=task_code,
            request_id=transport_req.id,
            pickup_location_id=pickup_location_id,
            dropoff_location_id=dropoff_location_id,
            cart_id=cart.id,
            status="created",
        )
        db.add(fleet_task)
        db.flush()

        self.create_fleet_task(db, fleet_task, request_type=transport_req.request_type)
        return fleet_task

    def receive_task_status(self, db: Session, payload: dict[str, Any]) -> Optional[TaskStatus]:
        """
        Process a status callback webhook from KUKA Fleet Manager (`/receive-status`).
        1. Persists a `TaskStatus` audit record in `task_status`.
        2. Maps KUKA status code (`6`: in_progress, `7`: failed, `3`: cancelled, `8`/`9`: completed).
        3. Updates `FleetTask`, `TransportRequest`, and `ItemStock` directly without any legacy Inbound/Outbound tables.
        """
        order_id = payload.get("orderId")
        if not order_id:
            raise ValueError("orderId is required")

        ics_status = str(payload.get("status") or "")
        mapped_status = MAPPING_STATUS.get(ics_status)

        record = TaskStatus(
            sub_task_status=str(payload.get("subTaskStatus")) if payload.get("subTaskStatus") is not None else None,
            order_id=str(order_id),
            device_code=payload.get("deviceCode"),
            device_num=str(payload.get("deviceNum")) if payload.get("deviceNum") is not None else None,
            qr_code=payload.get("qrCode"),
            shelf_number=payload.get("shelfNumber"),
            status=ics_status,
        )
        db.add(record)
        db.flush()

        fleet_task = (
            db.query(FleetTask)
            .filter(FleetTask.task_code == str(order_id))
            .first()
        )
        if not fleet_task:
            logger.warning("Received status for unknown FleetTask orderId=%s", order_id)
            db.commit()
            db.refresh(record)
            return record

        if fleet_task.status == "completed":
            db.commit()
            db.refresh(record)
            return record

        if payload.get("deviceCode") or payload.get("deviceNum"):
            fleet_task.amr_code = str(payload.get("deviceCode") or payload.get("deviceNum"))

        if mapped_status == "in_progress":
            fleet_task.status = "in_progress"
            if fleet_task.request:
                fleet_task.request.status = "in_progress"
            db.commit()
        elif mapped_status == "completed":
            db.commit()
            self.complete_fleet_task(db, fleet_task.task_code)
        elif mapped_status in ("failed", "cancelled"):
            fleet_task.status = mapped_status
            fleet_task.error_message = f"Fleet reported {mapped_status} (raw status={ics_status})"
            if fleet_task.request:
                fleet_task.request.status = mapped_status
            if fleet_task.cart_id:
                cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.cart_id).first()
                if cart:
                    cart.is_locked = False
                    cart.locked_by_task_id = None
                    cart.destination_location_id = None
            db.commit()
        else:
            db.commit()

        db.refresh(record)
        return record

    def complete_fleet_task(self, db: Session, task_code: str) -> FleetTask:
        """
        Callback handler when KUKA RCS reports that an AMR has completed its dropoff:
        1. Moves `cart.location_id = fleet_task.dropoff_location_id`.
        2. Unlocks the cart (`is_locked = False`, `locked_by_task_id = None`, `destination_location_id = None`).
        3. Marks `FleetTask` and `TransportRequest` as `completed`.
        4. Triggers queue resolution (`try_resolve_waiting_slot_queue` & `try_resolve_waiting_cart_queue`)
           since the pickup location just became free and a cart just arrived!
        """
        fleet_task = (
            db.query(FleetTask)
            .filter(FleetTask.task_code == task_code)
            .with_for_update()
            .first()
        )
        if not fleet_task:
            raise ValueError(f"Không tìm thấy FleetTask '{task_code}'.")

        now = datetime.now(timezone.utc)
        fleet_task.status = "completed"
        fleet_task.completed_at = now

        if fleet_task.request:
            fleet_task.request.status = "completed"
            fleet_task.request.completed_at = now

        if fleet_task.cart_id:
            cart = db.query(ItemStock).filter(ItemStock.id == fleet_task.cart_id).first()
            if cart:
                cart.location_id = fleet_task.dropoff_location_id
                cart.destination_location_id = None
                cart.is_locked = False
                cart.locked_by_task_id = None

        db.commit()

        # Since pickup_location_id is now free, check if any queued request was waiting for a slot
        self.try_resolve_waiting_slot_queue(db)
        return fleet_task

    def try_resolve_waiting_cart_queue(self, db: Session, stage_level: int = 0) -> int:
        """
        Scan `TransportQueue` (`WAITING_CART`) in FIFO order (`priority ASC, created_at ASC`).
        If a cart is now available, lock it and dispatch a `FleetTask`.
        """
        pending_entries = (
            db.query(TransportQueue)
            .filter(
                TransportQueue.queue_type == "WAITING_CART",
                TransportQueue.status == "PENDING",
                TransportQueue.target_stage_level == stage_level,
            )
            .order_by(TransportQueue.priority.asc(), TransportQueue.created_at.asc())
            .with_for_update(skip_locked=True)
            .all()
        )

        resolved_count = 0
        for entry in pending_entries:
            req = entry.request
            if not req or not req.item_id:
                continue
            if not self._is_location_free(db, req.destination_location_id):
                continue

            cart = self.find_fifo_available_cart(
                db,
                item_id=req.item_id,
                stage_level=req.required_stage_level,
            )
            if cart:
                self._lock_cart_and_dispatch_fleet_task(
                    db=db,
                    transport_req=req,
                    cart=cart,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=req.destination_location_id,
                )
                entry.status = "RESOLVED"
                entry.resolved_at = datetime.now(timezone.utc)
                resolved_count += 1

        if resolved_count:
            db.commit()
        return resolved_count

    def try_resolve_waiting_slot_queue(self, db: Session) -> int:
        """
        Scan `TransportQueue` (`WAITING_SLOT`) in FIFO order (`priority ASC, created_at ASC`).
        When a CNC slot, Washing slot, or Empty Cart Buffer becomes free, dispatch the waiting cart.
        """
        pending_entries = (
            db.query(TransportQueue)
            .filter(
                TransportQueue.queue_type == "WAITING_SLOT",
                TransportQueue.status == "PENDING",
            )
            .order_by(TransportQueue.priority.asc(), TransportQueue.created_at.asc())
            .with_for_update(skip_locked=True)
            .all()
        )

        resolved_count = 0
        for entry in pending_entries:
            req = entry.request
            if not req or not req.cart_id:
                continue

            cart = db.query(ItemStock).filter(ItemStock.id == req.cart_id).first()
            if not cart or cart.is_locked or not cart.location_id:
                continue

            target_slot: Optional[Location] = None
            if req.request_type == "MOVE_TO_WASH":
                target_slot = self.find_available_slot_by_type(db, "WASHING_SLOT")
            elif req.request_type == "RETURN_EMPTY_CART":
                target_slot = self.find_available_slot_by_type(db, "EMPTY_CART_BUFFER")
            elif req.request_type == "MOVE_NEXT_STAGE":
                route = (
                    db.query(ProductionRoute)
                    .filter(
                        ProductionRoute.item_id == cart.item_id,
                        ProductionRoute.is_active.is_(True),
                    )
                    .first()
                )
                if route:
                    step = (
                        db.query(RouteStep)
                        .options(
                            joinedload(RouteStep.allowed_machine_links).joinedload(RouteStepMachine.machine)
                        )
                        .filter(
                            RouteStep.route_id == route.id,
                            RouteStep.stage_level == entry.target_stage_level,
                        )
                        .first()
                    )
                    if step:
                        allowed_machine_ids = [
                            link.machine_id for link in (step.allowed_machine_links or []) if link.machine_id
                        ]
                        target_slot = self.find_available_slot_for_machines(
                            db,
                            step.allowed_machines,
                            allowed_machine_ids=allowed_machine_ids,
                        )

            if target_slot:
                self._lock_cart_and_dispatch_fleet_task(
                    db=db,
                    transport_req=req,
                    cart=cart,
                    pickup_location_id=cart.location_id,
                    dropoff_location_id=target_slot.id,
                )
                entry.status = "RESOLVED"
                entry.resolved_at = datetime.now(timezone.utc)
                resolved_count += 1

        if resolved_count:
            db.commit()
        return resolved_count


dispatch_service = DispatchService()
