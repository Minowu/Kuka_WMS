"""Cart eligibility rule-chain for diagnostic logging and peer filtering."""

from typing import Callable, Optional

from app.core.logger import get_logger
from app.modules.production.dispatch.cart_route_rules import (
    log_peer_step_reject,
    peer_step_reject_reason,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("wms.dispatch")

PEER_REASONS = frozenset({"same_step_peer", "route_step_unresolved"})


def first_reject_reason(
    cart: ItemStock,
    cart_location: Optional[Location],
    *,
    stage_level: int,
    location_types: list[str],
    target_location: Optional[Location],
    machine_step_map: dict[int, tuple[int, int]],
    apply_peer_rule: bool,
) -> Optional[str]:
    """
    Rule chain: trả về reason đầu tiên khiến xe không đủ điều kiện, hoặc None nếu pass.
    Thứ tự giữ nguyên logic if/elif cũ.
    """
    rules: list[Callable[[], Optional[str]]] = [
        lambda: (
            f"stage mismatch (cart level {cart.current_stage_level} != required {stage_level})"
            if cart.current_stage_level != stage_level
            else None
        ),
        lambda: (
            f"already reserved/locked (mission={cart.locked_by_mission_code})"
            if cart.is_locked
            else None
        ),
        lambda: "cart status is empty" if cart.status == "empty" else None,
        lambda: (
            "location inactive or missing"
            if (not cart_location or not cart_location.is_active)
            else None
        ),
        lambda: (
            f"location type '{cart_location.location_type}' not in allowed {location_types}"
            if cart_location and cart_location.location_type not in location_types
            else None
        ),
        lambda: (
            f"position occupied at target location '{target_location.location_code}'"
            if target_location is not None and cart.location_id == target_location.id
            else None
        ),
        lambda: (
            f"position occupied on same machine (machine_id={target_location.machine_id})"
            if (
                target_location is not None
                and target_location.machine_id is not None
                and cart_location is not None
                and cart_location.machine_id == target_location.machine_id
            )
            else None
        ),
        lambda: peer_step_reject_reason(
            cart_location=cart_location,
            target_location=target_location,
            machine_step_map=machine_step_map,
            apply_peer_rule=apply_peer_rule,
        ),
    ]

    for rule in rules:
        reason = rule()
        if reason:
            return reason
    return None


def log_reject_or_eligible(
    cart: ItemStock,
    cart_location: Optional[Location],
    *,
    reason: Optional[str],
    item_id: int,
    target_location: Optional[Location],
    machine_step_map: dict[int, tuple[int, int]],
) -> None:
    """Ghi log truy xuất theo reason (peer = info/warning, còn lại = debug)."""
    loc_code = (
        cart_location.location_code
        if cart_location
        else str(cart.location_id)
    )

    if reason is None:
        logger.debug(
            "Cart %s considered eligible candidate at location %s (stage=%s)",
            cart.container_code,
            loc_code,
            cart.current_stage_level,
            extra={"container_code": cart.container_code, "station_code": loc_code},
        )
        return

    if reason in PEER_REASONS:
        log_peer_step_reject(
            cart=cart,
            cart_location=cart_location,
            target_location=target_location,
            item_id=item_id,
            machine_step_map=machine_step_map,
            reason=reason,
        )
        return

    logger.debug(
        "Cart %s rejected: %s",
        cart.container_code,
        reason,
        extra={"container_code": cart.container_code, "reason": reason},
    )


def log_candidate_pool(
    carts: list[ItemStock],
    *,
    item_id: int,
    stage_level: int,
    location_types: list[str],
    target_location: Optional[Location],
    machine_step_map: dict[int, tuple[int, int]],
    apply_peer_rule: bool,
) -> None:
    """Đánh giá và log toàn bộ ứng viên active (diagnostic, không đổi selection)."""
    for cart in carts:
        reason = first_reject_reason(
            cart,
            cart.location,
            stage_level=stage_level,
            location_types=location_types,
            target_location=target_location,
            machine_step_map=machine_step_map,
            apply_peer_rule=apply_peer_rule,
        )
        log_reject_or_eligible(
            cart,
            cart.location,
            reason=reason,
            item_id=item_id,
            target_location=target_location,
            machine_step_map=machine_step_map,
        )
