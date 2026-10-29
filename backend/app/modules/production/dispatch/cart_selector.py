"""Cart Selection & Location Geometry Service for KUKA WMS."""

from datetime import datetime, timezone
import math
from typing import Optional

from sqlalchemy.orm import Session, joinedload, lazyload

from app.modules.production.production_models import (
    FleetTask,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location


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

        # Trường hợp 1: stage_level == 0 hoặc vị trí đích không có tọa độ -> thuần FIFO, chỉ khóa ĐÚNG 1 dòng!
        if (
            stage_level <= 0
            or target_location is None
            or target_location.map_x is None
            or target_location.map_y is None
        ):
            return (
                base_query.options(lazyload("*"))
                .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
                .with_for_update(of=ItemStock, skip_locked=True)
                .first()
            )

        # Trường hợp 2: stage_level > 0 có tọa độ vị trí đích -> tính khoảng cách 2D trên danh sách chưa khóa,
        # sau đó mới khóa dòng (FOR UPDATE SKIP LOCKED) trên xe ứng viên gần nhất còn rảnh.
        unlocked_candidates = (
            base_query.options(lazyload("*"), joinedload(ItemStock.location))
            .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
            .all()
        )
        if not unlocked_candidates:
            return None

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
                return locked_cart

        return None

    def is_location_free(self, db: Session, location_id: int) -> bool:
        """
        A location is free if:
        1. No active cart is currently sitting at `location_id`.
        2. No cart in-transit has `destination_location_id == location_id` (locked cart).
        3. No active `FleetTask` has `dropoff_location_id == location_id`.
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
                FleetTask.status.in_(["created", "pending_submit", "submitting", "sent", "in_progress"]),
            )
            .first()
        )
        if reserved_by_task:
            return False

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
                return slot
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
                return slot
        return None
