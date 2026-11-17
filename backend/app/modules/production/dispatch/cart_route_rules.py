"""Route-based rules for CNC cart selection (stage map + same-step peer ban)."""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import get_logger
from app.modules.production.production_models import (
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("wms.dispatch")


def load_machine_step_map(
    db: Session,
    item_id: int,
) -> dict[int, tuple[int, int]]:
    """
    Tiền nạp map `machine_id -> (step_number, stage_level)` từ ProductionRoute đang active.
    Dùng để cấm bắt cặp hai máy cùng bước (cùng step_number VÀ cùng stage_level).
    """
    route = (
        db.query(ProductionRoute)
        .options(
            joinedload(ProductionRoute.steps).joinedload(
                RouteStep.allowed_machine_links
            )
        )
        .filter(
            ProductionRoute.item_id == item_id,
            ProductionRoute.is_active.is_(True),
        )
        .first()
    )
    if not route:
        return {}

    result: dict[int, tuple[int, int]] = {}
    for step in route.steps or []:
        key = (int(step.step_number), int(step.stage_level))
        for link in step.allowed_machine_links or []:
            if link.machine_id is not None:
                result[int(link.machine_id)] = key
    return result


def machine_code_of(loc: Optional[Location]) -> Optional[str]:
    if not loc:
        return None
    machine = getattr(loc, "machine", None)
    if machine and getattr(machine, "machine_code", None):
        return machine.machine_code
    return str(loc.machine_id) if loc.machine_id is not None else None


def peer_step_reject_reason(
    *,
    cart_location: Optional[Location],
    target_location: Optional[Location],
    machine_step_map: dict[int, tuple[int, int]],
    apply_peer_rule: bool,
) -> Optional[str]:
    """
    Trả về reason code nếu xe bị loại bởi luật cùng bước / thiếu map route.
    - `same_step_peer`: cùng step_number VÀ cùng stage_level với máy đích.
    - `route_step_unresolved`: không tra được bước cho máy xe hoặc máy đích.
    Xe ở RAW (không có machine_id) không bị luật này chặn.
    """
    if not apply_peer_rule or not target_location or target_location.machine_id is None:
        return None
    if not cart_location or cart_location.machine_id is None:
        return None

    dest_key = machine_step_map.get(int(target_location.machine_id))
    cart_key = machine_step_map.get(int(cart_location.machine_id))
    if dest_key is None or cart_key is None:
        return "route_step_unresolved"
    if cart_key[0] == dest_key[0] and cart_key[1] == dest_key[1]:
        return "same_step_peer"
    return None


def log_peer_step_reject(
    *,
    cart: ItemStock,
    cart_location: Optional[Location],
    target_location: Optional[Location],
    item_id: int,
    machine_step_map: dict[int, tuple[int, int]],
    reason: str,
) -> None:
    cart_mid = cart_location.machine_id if cart_location else None
    dest_mid = target_location.machine_id if target_location else None
    cart_key = machine_step_map.get(int(cart_mid)) if cart_mid is not None else None
    dest_key = machine_step_map.get(int(dest_mid)) if dest_mid is not None else None
    pickup_code = cart_location.location_code if cart_location else None
    dest_code = target_location.location_code if target_location else None
    extra = {
        "container_code": cart.container_code,
        "item_id": item_id,
        "pickup_location_code": pickup_code,
        "dest_location_code": dest_code,
        "pickup_machine_code": machine_code_of(cart_location),
        "dest_machine_code": machine_code_of(target_location),
        "cart_step_number": cart_key[0] if cart_key else None,
        "cart_stage_level": cart_key[1] if cart_key else None,
        "dest_step_number": dest_key[0] if dest_key else None,
        "dest_stage_level": dest_key[1] if dest_key else None,
        "reason": reason,
    }
    if reason == "same_step_peer":
        logger.info(
            "Cart %s rejected: same_step_peer (pickup=%s machine=%s -> dest=%s machine=%s, "
            "step_number=%s stage_level=%s)",
            cart.container_code,
            pickup_code,
            extra["pickup_machine_code"],
            dest_code,
            extra["dest_machine_code"],
            extra["cart_step_number"],
            extra["cart_stage_level"],
            extra=extra,
        )
    else:
        logger.warning(
            "Cart %s rejected: route_step_unresolved (pickup=%s machine=%s -> dest=%s machine=%s, "
            "item_id=%s)",
            cart.container_code,
            pickup_code,
            extra["pickup_machine_code"],
            dest_code,
            extra["dest_machine_code"],
            item_id,
            extra=extra,
        )


def get_stage_info_for_machine(
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
            .options(
                joinedload(RouteStep.allowed_machine_links).joinedload(
                    RouteStepMachine.machine
                )
            )
            .filter(RouteStep.route_id == route.id)
            .order_by(RouteStep.stage_level.asc(), RouteStep.step_number.asc())
            .all()
        )

    machine_id = location.machine_id
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
