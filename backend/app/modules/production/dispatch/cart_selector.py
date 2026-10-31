"""Cart Selection & Location Geometry Service for KUKA WMS."""

from datetime import datetime, timezone
import math
from typing import Optional

from sqlalchemy.orm import Session, joinedload, lazyload

from app.core.logger import get_logger
from app.modules.production.production_models import (
    FleetTask,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("wms.dispatch")


class CartSelector:
    """Handles cart searching (FIFO / Euclidean 2D), slot availability, and route inspection."""

    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """2D Euclidean distance between two map nodes."""
        x1 = loc1.map_x or 0
        y1 = loc1.map_y or 0
        x2 = loc2.map_x or 0
        y2 = loc2.map_y or 0
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def get_stage_info_for_machine(
        self,
        db: Session,
        location: Location,
        item_id: int,
    ) -> tuple[int, int, bool]:
        """
        Resolve `(input_required_level, target_stage_level, is_final_cnc_step)` for a CNC `location`
        machining `item_id` using the normalized 3NF `ProductionRoute` -> `RouteStep` -> `RouteStepMachine`.
        """
        route = (
            db.query(ProductionRoute)
            .filter(
                ProductionRoute.item_id == item_id,
                ProductionRoute.is_active.is_(True),
            )
            .first()
        )
        steps: list[RouteStep] = []
        if route:
            steps = (
                db.query(RouteStep)
                .options(joinedload(RouteStep.allowed_machine_links).joinedload(RouteStepMachine.machine))
                .filter(RouteStep.route_id == route.id)
                .order_by(RouteStep.stage_level.asc(), RouteStep.step_number.asc())
                .all()
            )

        machine_id = location.machine_id

        # 1. Match via normalized 3NF RouteStepMachine links
        if steps and machine_id:
            for idx, step in enumerate(steps):
                matched = any(
                    link.machine_id == machine_id
                    for link in (step.allowed_machine_links or [])
                )
                if matched:
                    input_lvl = max(step.stage_level - 1, 0)
                    is_final = bool(step.is_final_cnc_step) or (idx == len(steps) - 1)
                    return (input_lvl, step.stage_level, is_final)

        raise ValueError(
            f"Máy CNC tại vị trí '{location.location_code}' chưa được cấu hình trong bất kỳ công đoạn nào "
            f"của Quy trình sản xuất (Model ID={item_id}). Vui lòng gán Route cho máy trước khi vận hành."
        )

    def find_fifo_available_cart(
        self,
        db: Session,
        item_id: int,
        stage_level: int = 0,
        target_location: Optional[Location] = None,
    ) -> Optional[ItemStock]:
        """
        Tìm xe phôi rảnh phù hợp với `item_id` và `current_stage_level`:
        - Với `stage_level == 0` (Phôi thô): Sắp xếp theo thứ tự nhập trước xuất trước FIFO (`created_at ASC, id ASC`).
          Dùng `.first()` kết hợp `with_for_update(of=ItemStock, skip_locked=True)` để mỗi request
          chỉ khóa đúng 1 dòng xe phôi thay vì khóa toàn bộ kho phôi thô!
        - Với `stage_level > 0` (Chuyển phôi bán thành phẩm WIP giữa các máy CNC): Ưu tiên khoảng cách
          Euclid 2D gần nhất tới `target_location` (nếu có tọa độ bản đồ), nếu bằng nhau thì xét theo FIFO.
          Xếp hạng danh sách ứng viên trước (không giữ khóa DB), sau đó mới thử khóa lần lượt từng xe gần nhất.
        """
        location_types = ["RAW_MATERIAL"] if stage_level == 0 else ["CNC_SLOT", "RAW_MATERIAL"]

        # Log candidate evaluation: examine active carts for item_id and log consideration or rejection reasons
        candidate_pool = (
            db.query(ItemStock)
            .options(joinedload(ItemStock.location))
            .filter(
                ItemStock.item_id == item_id,
                ItemStock.is_active.is_(True),
            )
            .all()
        )
        for cand in candidate_pool:
            c_loc = cand.location
            loc_code = c_loc.location_code if c_loc else str(cand.location_id)
            if cand.current_stage_level != stage_level:
                reason = f"stage mismatch (cart level {cand.current_stage_level} != required {stage_level})"
                logger.debug(
                    "Cart %s rejected: %s",
                    cand.container_code,
                    reason,
                    extra={"container_code": cand.container_code, "reason": reason},
                )
            elif cand.is_locked:
                reason = f"already reserved/locked (mission={cand.locked_by_mission_code})"
                logger.debug(
                    "Cart %s rejected: %s",
                    cand.container_code,
                    reason,
                    extra={"container_code": cand.container_code, "reason": reason},
                )
            elif cand.status == "empty":
                reason = "cart status is empty"
                logger.debug(
                    "Cart %s rejected: %s",
                    cand.container_code,
                    reason,
                    extra={"container_code": cand.container_code, "reason": reason},
                )
            elif not c_loc or not c_loc.is_active:
                reason = "location inactive or missing"
                logger.debug(
                    "Cart %s rejected: %s",
                    cand.container_code,
                    reason,
                    extra={"container_code": cand.container_code, "reason": reason},
                )
            elif c_loc.location_type not in location_types:
                reason = f"location type '{c_loc.location_type}' not in allowed {location_types}"
                logger.debug(
                    "Cart %s rejected: %s",
                    cand.container_code,
                    reason,
                    extra={"container_code": cand.container_code, "reason": reason},
                )
            elif target_location is not None and cand.location_id == target_location.id:
                reason = f"position occupied at target location '{target_location.location_code}'"
                logger.debug(
                    "Cart %s rejected: %s",
                    cand.container_code,
                    reason,
                    extra={"container_code": cand.container_code, "reason": reason},
                )
            elif (
                target_location is not None
                and target_location.machine_id is not None
                and c_loc.machine_id == target_location.machine_id
            ):
                reason = f"position occupied on same machine (machine_id={target_location.machine_id})"
                logger.debug(
                    "Cart %s rejected: %s",
                    cand.container_code,
                    reason,
                    extra={"container_code": cand.container_code, "reason": reason},
                )
            else:
                logger.debug(
                    "Cart %s considered eligible candidate at location %s (stage=%s)",
                    cand.container_code,
                    loc_code,
                    cand.current_stage_level,
                    extra={"container_code": cand.container_code, "station_code": loc_code},
                )

        base_query = (
            db.query(ItemStock)
            .join(Location, ItemStock.location_id == Location.id)
            .filter(
                ItemStock.item_id == item_id,
                ItemStock.current_stage_level == stage_level,
                ItemStock.is_locked.is_(False),
                ItemStock.is_active.is_(True),
                ItemStock.status != "empty",
                Location.location_type.in_(location_types),
                Location.is_active.is_(True),
            )
        )

        if target_location is not None:
            # 1. Loại trừ xe đang nằm tại chính vị trí đích
            base_query = base_query.filter(ItemStock.location_id != target_location.id)
            # 2. Loại trừ xe đang nằm tại vị trí khác thuộc CÙNG MỘT MÁY (tránh AMR gắp xe từ POS1 sang POS2 của cùng 1 máy)
            if target_location.machine_id is not None:
                base_query = base_query.filter(
                    (Location.machine_id != target_location.machine_id) | (Location.machine_id.is_(None))
                )

        selected_cart: Optional[ItemStock] = None
        # Trường hợp 1: stage_level == 0 hoặc vị trí đích không có tọa độ -> thuần FIFO, chỉ khóa ĐÚNG 1 dòng!
        if (
            stage_level <= 0
            or target_location is None
            or target_location.map_x is None
            or target_location.map_y is None
        ):
            selected_cart = (
                base_query.options(lazyload("*"))
                .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
                .with_for_update(of=ItemStock, skip_locked=True)
                .first()
            )
        else:
            # Trường hợp 2: stage_level > 0 có tọa độ vị trí đích -> tính khoảng cách 2D trên danh sách chưa khóa,
            # sau đó mới khóa dòng (FOR UPDATE SKIP LOCKED) trên xe ứng viên gần nhất còn rảnh.
            unlocked_candidates = (
                base_query.options(lazyload("*"), joinedload(ItemStock.location))
                .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
                .all()
            )
            if unlocked_candidates:
                candidates_with_coords = [
                    c for c in unlocked_candidates if c.location and c.location.map_x is not None and c.location.map_y is not None
                ]
                if candidates_with_coords:
                    unlocked_candidates.sort(
                        key=lambda c: (
                            self.calculate_distance(c.location, target_location)
                            if (c.location and c.location.map_x is not None and c.location.map_y is not None)
                            else float("inf"),
                            c.created_at or datetime.min.replace(tzinfo=timezone.utc),
                            c.id,
                        )
                    )

                for cand in unlocked_candidates:
                    locked_cart = (
                        db.query(ItemStock)
                        .options(lazyload("*"))
                        .filter(
                            ItemStock.id == cand.id,
                            ItemStock.is_locked.is_(False),
                            ItemStock.is_active.is_(True),
                            ItemStock.status != "empty",
                            ItemStock.current_stage_level == stage_level,
                        )
                        .with_for_update(of=ItemStock, skip_locked=True)
                        .first()
                    )
                    if locked_cart:
                        selected_cart = locked_cart
                        break

        if selected_cart:
            logger.info(
                "Cart selected: container=%s (id=%s) at location_id=%s for item_id=%s, stage_level=%s",
                selected_cart.container_code,
                selected_cart.id,
                selected_cart.location_id,
                item_id,
                stage_level,
                extra={
                    "container_code": selected_cart.container_code,
                    "station_code": str(selected_cart.location_id),
                },
            )
            return selected_cart

        target_code = target_location.location_code if target_location else None
        logger.warning(
            "No eligible cart found for item_id=%s, stage_level=%s (target_location=%s)",
            item_id,
            stage_level,
            target_code,
            extra={"station_code": target_code},
        )
        return None

    def is_location_free(self, db: Session, location_id: int) -> bool:
        """
        A location is free if:
        1. No active cart is currently sitting at `location_id`.
        2. No cart in-transit has `destination_location_id == location_id` (locked cart).
        3. No active `FleetTask` has `dropoff_location_id == location_id`.
        """
        occupied_by_cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.location_id == location_id,
                ItemStock.is_active.is_(True),
            )
            .first()
        )
        if occupied_by_cart:
            logger.debug(
                "Location id=%s rejected: occupied by cart %s",
                location_id,
                occupied_by_cart.container_code,
                extra={"container_code": occupied_by_cart.container_code, "reason": "position occupied by active cart"},
            )
            return False

        reserved_by_cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.destination_location_id == location_id,
                ItemStock.is_locked.is_(True),
                ItemStock.is_active.is_(True),
            )
            .first()
        )
        if reserved_by_cart:
            logger.debug(
                "Location id=%s rejected: reserved for cart %s (mission=%s)",
                location_id,
                reserved_by_cart.container_code,
                reserved_by_cart.locked_by_mission_code,
                extra={"container_code": reserved_by_cart.container_code, "reason": "already reserved by locked cart"},
            )
            return False

        reserved_by_task = (
            db.query(FleetTask)
            .filter(
                FleetTask.dropoff_location_id == location_id,
                FleetTask.status.in_(["created", "pending_submit", "submitting", "sent", "in_progress"]),
            )
            .first()
        )
        if reserved_by_task:
            logger.debug(
                "Location id=%s rejected: reserved by FleetTask %s (status=%s)",
                location_id,
                reserved_by_task.mission_code,
                reserved_by_task.status,
                extra={"fleet_task_id": reserved_by_task.id, "reason": f"already reserved by FleetTask {reserved_by_task.status}"},
            )
            return False

        logger.debug("Location id=%s is free", location_id)
        return True

    def find_available_slot_to_wash(self, db: Session) -> Optional[Location]:
        """Tìm ô đỗ còn trống tại Khu Tẩy Rửa (location_type == 'WASHING_SLOT': WASH-01..04)."""
        candidate_slots = (
            db.query(Location)
            .filter(
                Location.location_type == "WASHING_SLOT",
                Location.is_active.is_(True),
            )
            .order_by(Location.position_index.asc().nullsfirst(), Location.id.asc())
            .all()
        )
        for slot in candidate_slots:
            if self.is_location_free(db, slot.id):
                logger.info(
                    "Selected wash slot: %s (id=%s)",
                    slot.location_code,
                    slot.id,
                    extra={"station_code": slot.location_code},
                )
                return slot
        logger.warning("No available wash slot found among %d candidates", len(candidate_slots))
        return None

    def find_next_empty_buffer_slot(self, db: Session) -> Optional[Location]:
        """
        Distribute empty carts sequentially (Round-Robin: 1 -> 2 -> 3 -> 4 -> 1) across
        `EMPTY_CART_BUFFER` locations so AMRs do not pile all empty carts onto slot 1.
        """
        buffer_slots = (
            db.query(Location)
            .filter(
                Location.location_type == "EMPTY_CART_BUFFER",
                Location.is_active.is_(True),
            )
            .order_by(Location.position_index.asc().nullsfirst(), Location.id.asc())
            .all()
        )
        if not buffer_slots:
            logger.warning("No EMPTY_CART_BUFFER locations configured in system")
            return None

        buffer_ids = [slot.id for slot in buffer_slots]
        last_task = (
            db.query(FleetTask)
            .filter(FleetTask.dropoff_location_id.in_(buffer_ids))
            .order_by(FleetTask.id.desc())
            .first()
        )

        if last_task and last_task.dropoff_location_id in buffer_ids:
            last_idx = buffer_ids.index(last_task.dropoff_location_id)
            ordered_slots = buffer_slots[last_idx + 1 :] + buffer_slots[: last_idx + 1]
        else:
            ordered_slots = buffer_slots

        for slot in ordered_slots:
            if self.is_location_free(db, slot.id):
                logger.info(
                    "Selected empty buffer slot: %s (id=%s)",
                    slot.location_code,
                    slot.id,
                    extra={"station_code": slot.location_code},
                )
                return slot
        logger.warning("No available empty buffer slot found among %d candidates", len(buffer_slots))
        return None
