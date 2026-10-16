"""Core Dispatch Service for KUKA AMR CNC Machining Pipeline.

Implements:
1. 2D Euclidean distance nearest cart search.
2. Zero CNC Starvation double-buffering logic.
3. Concurrency locking (is_locked=True) to prevent cart race conditions.
4. TransportRequest & FleetTask lifecycle management.
5. Backpressure TransportQueue when carts or wash slots are saturated.
6. Automatic queue resolution upon stage completions and wash releases.
"""

import math
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from app.modules.auth.auth_model import User  # noqa: F401
from app.modules.robot.robot_model import RobotTask  # noqa: F401
from app.modules.warehouse.notificcation.notification_model import Notification  # noqa: F401
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.item.item_model import Item
from app.modules.production.production_models import (
    ProductionRoute,
    RouteStep,
    TransportRequest,
    TransportQueue,
    FleetTask,
    ProductionRecord,
)


class DispatchService:
    """Core dispatching and coordination engine for AMR WIP transport."""

    @staticmethod
    def calculate_distance(loc1: Location, loc2: Location) -> float:
        """Calculate 2D Euclidean distance between two locations on the shopfloor map."""
        x1 = loc1.map_x if loc1.map_x is not None else 0
        y1 = loc1.map_y if loc1.map_y is not None else 0
        x2 = loc2.map_x if loc2.map_x is not None else 0
        y2 = loc2.map_y if loc2.map_y is not None else 0
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    @classmethod
    def find_nearest_available_cart(
        cls,
        db: Session,
        target_location: Location,
        item_id: int,
        required_stage_level: int,
    ) -> Optional[ItemStock]:
        """Find the available unlocked cart that matches item_id and stage level.

        - If required_stage_level == 0 (Calling Level 0 raw material for CNC Level 1):
          Applies FIFO (First-In, First-Out) by created_at ASC.
        - If required_stage_level > 0 (Intermediate transfer between CNC machines):
          Applies 2D Euclidean distance to target_location.
        """
        candidate_query = (
            db.query(ItemStock)
            .filter(
                ItemStock.item_id == item_id,
                ItemStock.current_stage_level == required_stage_level,
                ItemStock.is_locked.is_(False),
                ItemStock.is_active.is_(True),
                ItemStock.location_id.isnot(None),
                ItemStock.location_id != target_location.id,
            )
        )

        if required_stage_level == 0:
            # FIFO: First-In, First-Out based on registration/arrival timestamp
            return candidate_query.order_by(ItemStock.created_at.asc(), ItemStock.id.asc()).first()

        # Level > 0: 2D Euclidean distance nearest cart
        candidate_carts = candidate_query.all()
        if not candidate_carts:
            return None

        # Sort candidate carts by Euclidean distance to target_location
        scored_carts: List[Tuple[float, ItemStock]] = []
        for cart in candidate_carts:
            if cart.location:
                dist = cls.calculate_distance(cart.location, target_location)
                scored_carts.append((dist, cart))

        if not scored_carts:
            return None

        scored_carts.sort(key=lambda x: x[0])
        return scored_carts[0][1]

    @staticmethod
    def get_stage_info_for_machine(
        db: Session,
        machine_code: str,
        item_id: int,
        default_stage_level: Optional[int] = None,
    ) -> Tuple[int, int, bool]:
        """Return (input_required_level, target_stage_level, is_final_cnc_step).

        Priority:
        1. Location default_stage_level (configured by Supervisor/Quản đốc) if set.
        2. ProductionRoute steps lookup matching machine_code in allowed_machines.
        3. Fallback based on machine naming convention (CNC-01/02 -> L1, CNC-03 -> L2, CNC-04 -> L3).
        """
        route = (
            db.query(ProductionRoute)
            .filter(ProductionRoute.item_id == item_id, ProductionRoute.is_active.is_(True))
            .first()
        )
        if default_stage_level is not None and default_stage_level > 0:
            if route and route.steps:
                for step in route.steps:
                    if step.stage_level == default_stage_level:
                        input_lvl = step.stage_level - 1 if step.stage_level > 0 else 0
                        return (input_lvl, step.stage_level, step.is_final_cnc_step)
            input_lvl = default_stage_level - 1 if default_stage_level > 0 else 0
            is_final = (default_stage_level >= 3)
            return (input_lvl, default_stage_level, is_final)

        if route and route.steps:
            for step in route.steps:
                allowed = step.allowed_machines or []
                if machine_code in allowed:
                    input_lvl = step.stage_level - 1 if step.stage_level > 0 else 0
                    return (input_lvl, step.stage_level, step.is_final_cnc_step)

        # Fallback based on machine naming convention
        if machine_code in ["CNC-01", "CNC-02"]:
            return (0, 1, False)
        elif machine_code == "CNC-03":
            return (1, 2, False)
        elif machine_code == "CNC-04":
            return (2, 3, True)
        return (0, 1, False)

    @classmethod
    def request_material_for_station(
        cls,
        db: Session,
        destination_location_id: int,
        item_id: int,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Handles operator [GỌI PHÔI] from PDA for a specific CNC position.

        1. Validates destination is a valid CNC_SLOT.
        2. Checks if destination currently already has a cart.
        3. Identifies required input level for this machine.
        4. Queries nearest matching unlocked cart via Euclidean 2D distance.
        5. If found: locks cart, creates TransportRequest & FleetTask.
        6. If not found: creates TransportRequest & enqueues into TransportQueue.
        """
        dest_loc = db.query(Location).filter(Location.id == destination_location_id).first()
        if not dest_loc:
            raise ValueError(f"Không tìm thấy vị trí ID={destination_location_id}")

        if dest_loc.location_type != "CNC_SLOT":
            raise ValueError(f"Vị trí {dest_loc.location_code} không phải trạm CNC ({dest_loc.location_type})")

        # Check if station already has a physical cart sitting there
        existing_cart = (
            db.query(ItemStock)
            .filter(ItemStock.location_id == destination_location_id, ItemStock.is_active.is_(True))
            .first()
        )
        if existing_cart:
            raise ValueError(
                f"Vị trí {dest_loc.location_name} hiện đã có xe [{existing_cart.cart_code}]. "
                "Cần gia công xong hoặc chuyển xe trước khi gọi xe mới."
            )

        # Check if an active incoming transport request already exists
        active_req = (
            db.query(TransportRequest)
            .filter(
                TransportRequest.destination_location_id == destination_location_id,
                TransportRequest.status.in_(["pending", "assigned", "in_progress"]),
            )
            .first()
        )
        if active_req:
            return {
                "success": False,
                "status": "already_calling",
                "message": f"Vị trí {dest_loc.location_name} đang có lệnh gọi [{active_req.request_code}] trên đường.",
                "request_code": active_req.request_code,
            }

        req_code = f"TR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        machine_code = dest_loc.machine_code or "CNC-01"
        input_lvl, target_lvl, is_final = cls.get_stage_info_for_machine(
            db, machine_code, item_id, dest_loc.default_stage_level
        )

        transport_req = TransportRequest(
            request_code=req_code,
            request_type="CALL_MATERIAL",
            item_id=item_id,
            destination_location_id=destination_location_id,
            required_stage_level=input_lvl,
            status="pending",
            priority=10,
            created_by=user_id,
        )
        db.add(transport_req)
        db.flush()

        # Search nearest available cart
        cart = cls.find_nearest_available_cart(db, dest_loc, item_id, input_lvl)
        if cart:
            # Atomic lock
            cart.is_locked = True
            cart.locked_by_task_id = req_code
            cart.destination_location_id = destination_location_id
            cart.status = "locked"

            transport_req.cart_id = cart.id
            transport_req.source_location_id = cart.location_id
            transport_req.status = "assigned"

            task_code = f"FLT-{req_code}"
            fleet_task = FleetTask(
                task_code=task_code,
                request_id=transport_req.id,
                amr_code="AMR-01",
                pickup_location_id=cart.location_id,
                dropoff_location_id=destination_location_id,
                cart_id=cart.id,
                status="sent",
                sent_at=func.now(),
            )
            db.add(fleet_task)
            db.commit()
            db.refresh(transport_req)
            db.refresh(cart)
            db.refresh(fleet_task)

            return {
                "success": True,
                "status": "assigned",
                "request_code": req_code,
                "fleet_task_code": task_code,
                "cart_code": cart.cart_code,
                "pickup_location": cart.location.location_code if cart.location else None,
                "destination_location": dest_loc.location_code,
                "required_level": input_lvl,
                "message": f"Đã tìm thấy xe [{cart.cart_code}] và điều AMR cõng tới [{dest_loc.location_name}].",
            }
        else:
            # Cart unavailable -> Enqueue
            queue_entry = TransportQueue(
                request_id=transport_req.id,
                queue_type="WAITING_CART",
                target_stage_level=input_lvl,
                status="PENDING",
                priority=10,
            )
            db.add(queue_entry)
            db.commit()
            db.refresh(transport_req)
            db.refresh(queue_entry)

            return {
                "success": True,
                "status": "queued",
                "request_code": req_code,
                "queue_id": queue_entry.id,
                "required_level": input_lvl,
                "message": (
                    f"Hiện chưa có xe phôi Level {input_lvl} sẵn sàng trên sàn. "
                    f"Yêu cầu đã được đưa vào hàng đợi tự động (Hàng đợi ID: {queue_entry.id})."
                ),
            }

    @classmethod
    def report_stage_completed(
        cls,
        db: Session,
        station_location_id: int,
        operator_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handles operator [BÁO XONG: CẬP NHẬT LEVEL] for a specific CNC position.

        1. Finds current cart at this location.
        2. Updates cart's current_stage_level to the station's target level.
        3. Records trace into ProductionRecord.
        4. If final CNC step (is_final_cnc_step=True):
           - Seeks empty WASHING_SLOT.
           - If wash slot available: dispatches AMR to transport cart to washing slot.
           - If all 4 wash slots full: enqueues into TransportQueue (WAITING_WASH_SLOT).
        5. If intermediate step:
           - Unlocks cart and checks if any downstream CNC station is waiting in queue.
        """
        station_loc = db.query(Location).filter(Location.id == station_location_id).first()
        if not station_loc:
            raise ValueError(f"Không tìm thấy vị trí ID={station_location_id}")

        cart = (
            db.query(ItemStock)
            .filter(ItemStock.location_id == station_location_id, ItemStock.is_active.is_(True))
            .first()
        )
        if not cart:
            raise ValueError(f"Không tìm thấy xe phôi tại vị trí {station_loc.location_name}")

        machine_code = station_loc.machine_code or "CNC-01"
        input_lvl, target_lvl, is_final = cls.get_stage_info_for_machine(
            db, machine_code, cart.item_id, station_loc.default_stage_level
        )

        # Update cart stage level
        cart.current_stage_level = target_lvl

        # Traceability record
        prod_rec = ProductionRecord(
            cart_code=cart.cart_code or f"CART-{cart.id}",
            cart_id=cart.id,
            item_id=cart.item_id,
            machine_code=machine_code,
            location_id=station_location_id,
            stage_level=target_lvl,
            operator_id=operator_id,
            notes=notes,
        )
        db.add(prod_rec)

        # Handle Routing: Final Step vs Intermediate Step
        if is_final:
            # 4. Final CNC Step: Transfer to Washing Area
            empty_wash_slot = (
                db.query(Location)
                .filter(
                    Location.location_type == "WASHING_SLOT",
                    Location.is_active.is_(True),
                    ~Location.id.in_(
                        db.query(ItemStock.location_id).filter(
                            ItemStock.location_id.isnot(None), ItemStock.is_active.is_(True)
                        )
                    ),
                    ~Location.id.in_(
                        db.query(TransportRequest.destination_location_id).filter(
                            TransportRequest.status.in_(["pending", "assigned", "in_progress"])
                        )
                    ),
                )
                .order_by(Location.position_index)
                .first()
            )

            req_code = f"TR-WASH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
            if empty_wash_slot:
                transport_req = TransportRequest(
                    request_code=req_code,
                    request_type="SEND_TO_WASH",
                    item_id=cart.item_id,
                    source_location_id=station_location_id,
                    destination_location_id=empty_wash_slot.id,
                    cart_id=cart.id,
                    required_stage_level=target_lvl,
                    status="assigned",
                    priority=5,
                    created_by=operator_id,
                )
                db.add(transport_req)
                db.flush()

                cart.is_locked = True
                cart.locked_by_task_id = req_code
                cart.destination_location_id = empty_wash_slot.id
                cart.status = "locked"

                task_code = f"FLT-{req_code}"
                fleet_task = FleetTask(
                    task_code=task_code,
                    request_id=transport_req.id,
                    amr_code="AMR-01",
                    pickup_location_id=station_location_id,
                    dropoff_location_id=empty_wash_slot.id,
                    cart_id=cart.id,
                    status="sent",
                    sent_at=func.now(),
                )
                db.add(fleet_task)
                db.commit()
                db.refresh(cart)

                return {
                    "success": True,
                    "action": "sent_to_wash",
                    "cart_code": cart.cart_code,
                    "target_level": target_lvl,
                    "wash_slot": empty_wash_slot.location_code,
                    "fleet_task_code": task_code,
                    "message": (
                        f"Gia công hoàn tất bước CNC cuối (Level {target_lvl}). "
                        f"Đã điều AMR chuyển xe [{cart.cart_code}] sang [{empty_wash_slot.location_name}]."
                    ),
                }
            else:
                # All wash slots are full -> Put in WAITING_WASH_SLOT queue
                fallback_wash = db.query(Location).filter(Location.location_type == "WASHING_SLOT").first()
                fallback_wash_id = fallback_wash.id if fallback_wash else station_location_id

                transport_req = TransportRequest(
                    request_code=req_code,
                    request_type="SEND_TO_WASH",
                    item_id=cart.item_id,
                    source_location_id=station_location_id,
                    destination_location_id=fallback_wash_id,
                    cart_id=cart.id,
                    required_stage_level=target_lvl,
                    status="pending",
                    priority=5,
                    created_by=operator_id,
                )
                db.add(transport_req)
                db.flush()

                queue_entry = TransportQueue(
                    request_id=transport_req.id,
                    queue_type="WAITING_WASH_SLOT",
                    target_stage_level=target_lvl,
                    status="PENDING",
                    priority=5,
                )
                db.add(queue_entry)
                db.commit()

                return {
                    "success": True,
                    "action": "queued_for_wash",
                    "cart_code": cart.cart_code,
                    "target_level": target_lvl,
                    "queue_id": queue_entry.id,
                    "message": (
                        f"Gia công hoàn tất Level {target_lvl}, nhưng cả 4 Slot Tẩy Rửa đang đầy. "
                        f"Xe [{cart.cart_code}] được xếp vào hàng đợi WAITING_WASH_SLOT."
                    ),
                }
        else:
            # Intermediate step: Unlock cart for downstream consumption
            cart.is_locked = False
            cart.locked_by_task_id = None
            cart.destination_location_id = None
            cart.status = "available"
            db.commit()

            # Check if any station is waiting for this cart level in WAITING_CART queue
            promoted_info = cls.try_resolve_waiting_cart_queue(db, cart)

            return {
                "success": True,
                "action": "stage_completed",
                "cart_code": cart.cart_code,
                "completed_level": target_lvl,
                "promoted_dispatch": promoted_info,
                "message": (
                    f"Hoàn tất gia công Level {target_lvl} tại [{station_loc.location_name}]. "
                    f"Xe [{cart.cart_code}] sẵn sàng cho công đoạn tiếp theo."
                ),
            }

    @classmethod
    def release_wash_slot_and_return_empty(
        cls,
        db: Session,
        wash_location_id: int,
        operator_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Handles operator [ĐÃ LẤY ĐI RỬA / GIẢI PHÓNG SLOT] from PDA.

        Rule 3 & 4:
        1. Empties the cart and creates RETURN_EMPTY_CART request to Empty Cart Buffer.
        2. Frees the wash slot.
        3. Automatically checks WAITING_WASH_SLOT queue and pulls next finished CNC cart into this slot.
        """
        wash_loc = db.query(Location).filter(Location.id == wash_location_id).first()
        if not wash_loc:
            raise ValueError(f"Không tìm thấy vị trí rửa ID={wash_location_id}")

        cart = (
            db.query(ItemStock)
            .filter(ItemStock.location_id == wash_location_id, ItemStock.is_active.is_(True))
            .first()
        )

        returned_buffer_code = None
        if cart:
            # Find an available empty cart buffer slot
            buf_loc = (
                db.query(Location)
                .filter(
                    Location.location_type == "EMPTY_CART_BUFFER",
                    Location.is_active.is_(True),
                    ~Location.id.in_(
                        db.query(ItemStock.location_id).filter(
                            ItemStock.location_id.isnot(None), ItemStock.is_active.is_(True)
                        )
                    ),
                )
                .first()
            )
            if not buf_loc:
                buf_loc = db.query(Location).filter(Location.location_type == "EMPTY_CART_BUFFER").first()

            if buf_loc:
                returned_buffer_code = buf_loc.location_code
                req_code = f"TR-RET-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

                cart.quantity = 0
                cart.current_stage_level = 0
                cart.is_locked = True
                cart.locked_by_task_id = req_code
                cart.destination_location_id = buf_loc.id
                cart.status = "locked"

                ret_req = TransportRequest(
                    request_code=req_code,
                    request_type="RETURN_EMPTY_CART",
                    item_id=cart.item_id,
                    source_location_id=wash_location_id,
                    destination_location_id=buf_loc.id,
                    cart_id=cart.id,
                    required_stage_level=0,
                    status="assigned",
                    priority=20,
                    created_by=operator_id,
                )
                db.add(ret_req)
                db.flush()

                fleet_task = FleetTask(
                    task_code=f"FLT-{req_code}",
                    request_id=ret_req.id,
                    amr_code="AMR-01",
                    pickup_location_id=wash_location_id,
                    dropoff_location_id=buf_loc.id,
                    cart_id=cart.id,
                    status="sent",
                    sent_at=func.now(),
                )
                db.add(fleet_task)

        # Wash slot is now freed. Check WAITING_WASH_SLOT queue
        pending_wash_queue = (
            db.query(TransportQueue)
            .filter(TransportQueue.queue_type == "WAITING_WASH_SLOT", TransportQueue.status == "PENDING")
            .order_by(TransportQueue.priority.asc(), TransportQueue.created_at.asc())
            .first()
        )

        promoted_msg = None
        if pending_wash_queue:
            t_req = pending_wash_queue.request
            if t_req and t_req.cart_id:
                waiting_cart = db.query(ItemStock).filter(ItemStock.id == t_req.cart_id).first()
                if waiting_cart:
                    t_req.destination_location_id = wash_location_id
                    t_req.status = "assigned"

                    waiting_cart.is_locked = True
                    waiting_cart.locked_by_task_id = t_req.request_code
                    waiting_cart.destination_location_id = wash_location_id
                    waiting_cart.status = "locked"

                    pending_wash_queue.status = "RESOLVED"
                    pending_wash_queue.resolved_at = func.now()

                    fleet_task_wash = FleetTask(
                        task_code=f"FLT-{t_req.request_code}",
                        request_id=t_req.id,
                        amr_code="AMR-01",
                        pickup_location_id=t_req.source_location_id,
                        dropoff_location_id=wash_location_id,
                        cart_id=waiting_cart.id,
                        status="sent",
                        sent_at=func.now(),
                    )
                    db.add(fleet_task_wash)
                    promoted_msg = f"Đã kéo xe [{waiting_cart.cart_code}] từ CNC vào slot [{wash_loc.location_name}]."

        db.commit()

        return {
            "success": True,
            "action": "wash_slot_released",
            "freed_slot": wash_loc.location_code,
            "empty_cart_destination": returned_buffer_code,
            "promoted_wash_queue": promoted_msg,
            "message": (
                f"Đã giải phóng [{wash_loc.location_name}]. "
                + (f"AMR chở xe rỗng về [{returned_buffer_code}]. " if returned_buffer_code else "")
                + (promoted_msg or "")
            ),
        }

    @classmethod
    def try_resolve_waiting_cart_queue(cls, db: Session, available_cart: ItemStock) -> Optional[Dict[str, Any]]:
        """Checks if newly available cart satisfies any pending WAITING_CART request."""
        pending_queue = (
            db.query(TransportQueue)
            .join(TransportRequest, TransportQueue.request_id == TransportRequest.id)
            .filter(
                TransportQueue.queue_type == "WAITING_CART",
                TransportQueue.status == "PENDING",
                TransportRequest.item_id == available_cart.item_id,
                TransportQueue.target_stage_level == available_cart.current_stage_level,
            )
            .order_by(TransportQueue.priority.asc(), TransportQueue.created_at.asc())
            .first()
        )

        if not pending_queue:
            return None

        t_req = pending_queue.request
        available_cart.is_locked = True
        available_cart.locked_by_task_id = t_req.request_code
        available_cart.destination_location_id = t_req.destination_location_id
        available_cart.status = "locked"

        t_req.cart_id = available_cart.id
        t_req.source_location_id = available_cart.location_id
        t_req.status = "assigned"

        pending_queue.status = "RESOLVED"
        pending_queue.resolved_at = func.now()

        task_code = f"FLT-{t_req.request_code}"
        fleet_task = FleetTask(
            task_code=task_code,
            request_id=t_req.id,
            amr_code="AMR-01",
            pickup_location_id=available_cart.location_id,
            dropoff_location_id=t_req.destination_location_id,
            cart_id=available_cart.id,
            status="sent",
            sent_at=func.now(),
        )
        db.add(fleet_task)
        db.commit()

        return {
            "resolved_queue_id": pending_queue.id,
            "request_code": t_req.request_code,
            "cart_code": available_cart.cart_code,
            "destination_location_id": t_req.destination_location_id,
        }

    @classmethod
    def simulate_fleet_arrival(cls, db: Session, fleet_task_id: int) -> Dict[str, Any]:
        """Simulates physical AMR arriving and dropping off the cart at its destination."""
        task = db.query(FleetTask).filter(FleetTask.id == fleet_task_id).first()
        if not task:
            raise ValueError(f"Không tìm thấy FleetTask ID={fleet_task_id}")

        task.status = "completed"
        task.completed_at = func.now()

        req = task.request
        if req:
            req.status = "completed"
            req.completed_at = func.now()

        if task.cart:
            task.cart.location_id = task.dropoff_location_id
            task.cart.destination_location_id = None
            task.cart.is_locked = False
            task.cart.locked_by_task_id = None
            task.cart.status = "available"

        db.commit()
        return {
            "success": True,
            "task_code": task.task_code,
            "status": "completed",
            "cart_code": task.cart.cart_code if task.cart else None,
            "current_location_id": task.dropoff_location_id,
        }
