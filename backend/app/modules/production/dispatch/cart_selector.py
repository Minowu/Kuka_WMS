"""Cart Selection & Location Geometry Service for KUKA WMS."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload, lazyload

from app.core.logger import get_logger
from app.modules.production.dispatch.cart_eligibility import log_candidate_pool
from app.modules.production.dispatch.cart_geometry import calculate_distance
from app.modules.production.dispatch.cart_route_rules import (
    get_stage_info_for_machine as resolve_stage_info_for_machine,
    load_machine_step_map,
    peer_step_reject_reason,
)
from app.modules.production.production_models import FleetTask
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("wms.dispatch")


class CartSelector:
    """Handles cart searching (FIFO / Euclidean 2D), slot availability, and route inspection."""

    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        return calculate_distance(loc1, loc2)

    def get_stage_info_for_machine(
        self,
        db: Session,
        location: Location,
        item_id: int,
    ) -> tuple[int, int, bool]:
        return resolve_stage_info_for_machine(db, location, item_id)

    def find_fifo_available_cart(
        self,
        db: Session,
        item_id: int,
        stage_level: int = 0,
        target_location: Optional[Location] = None,
    ) -> Optional[ItemStock]:
        """
        Tìm xe phôi rảnh phù hợp với `item_id` và `current_stage_level`:
        - `stage_level == 0`: FIFO thuần (+ FOR UPDATE SKIP LOCKED 1 dòng).
        - `stage_level > 0`: ưu tiên khoảng cách Euclid tới đích, hòa thì FIFO.
        - Luật WIP: không bắt cặp hai máy cùng step_number VÀ stage_level; thiếu map bước → loại xe.
        """
        location_types = ["RAW_MATERIAL"] if stage_level == 0 else ["CNC_SLOT", "RAW_MATERIAL"]
        apply_peer_rule = (
            stage_level > 0
            and target_location is not None
            and target_location.machine_id is not None
        )
        machine_step_map: dict[int, tuple[int, int]] = (
            load_machine_step_map(db, item_id) if apply_peer_rule else {}
        )

        candidate_pool = (
            db.query(ItemStock)
            .options(joinedload(ItemStock.location).joinedload(Location.machine))
            .filter(
                ItemStock.item_id == item_id,
                ItemStock.is_active.is_(True),
            )
            .all()
        )
        log_candidate_pool(
            candidate_pool,
            item_id=item_id,
            stage_level=stage_level,
            location_types=location_types,
            target_location=target_location,
            machine_step_map=machine_step_map,
            apply_peer_rule=apply_peer_rule,
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
            base_query = base_query.filter(ItemStock.location_id != target_location.id)
            if target_location.machine_id is not None:
                base_query = base_query.filter(
                    (Location.machine_id != target_location.machine_id)
                    | (Location.machine_id.is_(None))
                )

        selected_cart: Optional[ItemStock] = None
        if stage_level <= 0:
            selected_cart = (
                base_query.options(lazyload("*"))
                .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
                .with_for_update(of=ItemStock, skip_locked=True)
                .first()
            )
        else:
            unlocked_candidates = (
                base_query.options(
                    lazyload("*"),
                    joinedload(ItemStock.location).joinedload(Location.machine),
                )
                .order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
                .all()
            )
            filtered_candidates = [
                cand
                for cand in unlocked_candidates
                if not peer_step_reject_reason(
                    cart_location=cand.location,
                    target_location=target_location,
                    machine_step_map=machine_step_map,
                    apply_peer_rule=apply_peer_rule,
                )
            ]

            if (
                filtered_candidates
                and target_location is not None
                and target_location.map_x is not None
                and target_location.map_y is not None
            ):
                has_coords = any(
                    c.location
                    and c.location.map_x is not None
                    and c.location.map_y is not None
                    for c in filtered_candidates
                )
                if has_coords:
                    filtered_candidates.sort(
                        key=lambda c: (
                            calculate_distance(c.location, target_location)
                            if (
                                c.location
                                and c.location.map_x is not None
                                and c.location.map_y is not None
                            )
                            else float("inf"),
                            c.created_at or datetime.min.replace(tzinfo=timezone.utc),
                            c.id,
                        )
                    )

            for cand in filtered_candidates:
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
                extra={
                    "container_code": occupied_by_cart.container_code,
                    "reason": "position occupied by active cart",
                },
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
                extra={
                    "container_code": reserved_by_cart.container_code,
                    "reason": "already reserved by locked cart",
                },
            )
            return False

        reserved_by_task = (
            db.query(FleetTask)
            .filter(
                FleetTask.dropoff_location_id == location_id,
                FleetTask.status.in_(
                    ["created", "pending_submit", "submitting", "sent", "in_progress"]
                ),
            )
            .first()
        )
        if reserved_by_task:
            logger.debug(
                "Location id=%s rejected: reserved by FleetTask %s (status=%s)",
                location_id,
                reserved_by_task.mission_code,
                reserved_by_task.status,
                extra={
                    "fleet_task_id": reserved_by_task.id,
                    "reason": f"already reserved by FleetTask {reserved_by_task.status}",
                },
            )
            return False

        logger.debug("Location id=%s is free", location_id)
        return True

    def find_available_slot_to_wash(self, db: Session) -> Optional[Location]:
        """Tìm ô đỗ còn trống tại Khu Tẩy Rửa (location_type == 'WASHING_SLOT')."""
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
        logger.warning(
            "No available wash slot found among %d candidates", len(candidate_slots)
        )
        return None

    def find_next_empty_buffer_slot(self, db: Session) -> Optional[Location]:
        """
        Distribute empty carts sequentially (Round-Robin) across EMPTY_CART_BUFFER locations.
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
        logger.warning(
            "No available empty buffer slot found among %d candidates",
            len(buffer_slots),
        )
        return None
