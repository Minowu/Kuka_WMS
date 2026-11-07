"""Service layer for managing Production Routes and Route Steps (3NF)."""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import get_logger
from app.modules.production.production_models import (
    Machine,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportRequest,
)
from app.modules.production.route_schema import (
    ItemSummary,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
    RouteStepResponse,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

log = get_logger("wms.domain.production")

ACTIVE_ROUTE_REQUEST_STATUSES = (
    "pending",
    "queued_for_cart",
    "queued_for_slot",
    "in_progress",
)


def _find_blocking_cnc_wip_or_request(
    db: Session,
    item_id: int,
) -> tuple[Optional[str], Optional[str], dict]:
    """
    Kiểm tra xem sản phẩm `item_id` có đang vướng luồng gia công CNC hay lệnh vận chuyển không:
    - CHO PHÉP tạo / bật / tắt / sửa / xóa quy trình nếu xe phôi (`ItemStock`) chỉ đang nằm yên
      (`is_locked=False`) tại Khu Nguyên Liệu (`RAW_MATERIAL`), Khu Tẩy Rửa (`WASHING_SLOT`)
      hoặc Bãi Xe Trống (`EMPTY_CART_BUFFER`) và không có lệnh vận chuyển nào đang treo.
    - CHẶN nếu:
      1. Có xe phôi đang bị khóa di chuyển trên AMR (`is_locked=True` hoặc `location_id=None`).
      2. Có xe phôi đang nằm tại vị trí Máy CNC (`Location.location_type == 'CNC_SLOT'`).
      3. Có lệnh gọi hàng / vận chuyển (`TransportRequest`) của sản phẩm này đang ở trạng thái
         `pending`, `queued_for_cart`, `queued_for_slot`, `in_progress`
         (ngoại trừ lệnh trả xe rỗng `RETURN_EMPTY_CART`).
    """
    active_stocks = (
        db.query(ItemStock)
        .options(joinedload(ItemStock.location))
        .filter(
            ItemStock.item_id == item_id,
            ItemStock.is_active.is_(True),
            ItemStock.status != "empty",
        )
        .all()
    )

    for stock in active_stocks:
        container = stock.container_code or f"stock #{stock.id}"
        loc: Optional[Location] = stock.location

        # 1. Xe đang bị khóa bởi nhiệm vụ AMR hoặc đang được nhấc khỏi sàn (location_id is None)
        if stock.is_locked or loc is None:
            mission_info = (
                f" (nhiệm vụ: {stock.locked_by_mission_code})"
                if stock.locked_by_mission_code
                else ""
            )
            return (
                "stock_in_transit",
                f"xe phôi ({container}) đang trong lệnh vận chuyển AMR{mission_info}",
                {
                    "container_code": stock.container_code,
                    "reason": "stock_in_transit",
                },
            )

        # 2. Xe đang nằm dở dang tại vị trí Máy CNC (CNC_SLOT)
        if loc.location_type == "CNC_SLOT":
            loc_label = loc.location_name or loc.location_code
            return (
                "active_stock_at_cnc",
                f"xe phôi ({container}) đang gia công tại máy CNC '{loc_label}' (Level {stock.current_stage_level or 0})",
                {
                    "container_code": stock.container_code,
                    "station_code": loc.location_code,
                    "reason": "active_stock_at_cnc",
                },
            )

    # 3. Kiểm tra lệnh gọi hàng / hàng đợi vận chuyển đang hoạt động (trừ trả xe rỗng từ khu rửa)
    active_req = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.item_id == item_id,
            TransportRequest.status.in_(ACTIVE_ROUTE_REQUEST_STATUSES),
            TransportRequest.request_type != "RETURN_EMPTY_CART",
        )
        .order_by(TransportRequest.id.desc())
        .first()
    )
    if active_req:
        return (
            "active_transport_request",
            f"đang có lệnh gọi/vận chuyển hàng '{active_req.request_code}' (trạng thái: {active_req.status})",
            {
                "transport_request_id": active_req.id,
                "request_code": active_req.request_code,
                "reason": "active_transport_request",
            },
        )

    return None, None, {}


def _to_route_response(route: ProductionRoute, include_steps: bool = False):
    item_summary = None
    if route.item:
        item_summary = ItemSummary(
            id=route.item.id,
            sku=route.item.sku,
            name=route.item.name,
            standard_quantity_per_cart=getattr(route.item, "standard_quantity_per_cart", 120) or 120,
        )

    steps_list = route.steps or []
    base_data = {
        "id": route.id,
        "route_code": route.route_code,
        "route_name": route.route_name,
        "item_id": route.item_id,
        "version": route.version,
        "is_active": route.is_active,
        "step_count": len(steps_list),
        "item": item_summary,
        "created_at": route.created_at,
        "updated_at": route.updated_at,
    }

    if include_steps:
        return ProductionRouteDetailResponse(
            **base_data,
            steps=[RouteStepResponse.model_validate(s) for s in steps_list],
        )
    return ProductionRouteResponse(**base_data)


def _get_or_create_machine(
    db: Session,
    machine_code: str,
    warehouse_id: Optional[int] = None,
) -> Machine:
    code = machine_code.strip()
    machine = db.query(Machine).filter(Machine.machine_code == code).first()
    if machine is None:
        machine = Machine(
            machine_code=code,
            machine_name=f"Máy {code}",
            warehouse_id=warehouse_id,
        )
        db.add(machine)
        db.flush()
    return machine


def _sync_step_machines(
    db: Session,
    step: RouteStep,
    machine_codes: list[str],
    warehouse_id: Optional[int] = None,
) -> None:
    """Populate normalized RouteStepMachine join rows for a RouteStep."""
    old_links = db.query(RouteStepMachine).filter(RouteStepMachine.route_step_id == step.id).all()
    old_machines = {link.machine.machine_code for link in old_links if link.machine and link.machine.machine_code}

    db.query(RouteStepMachine).filter(RouteStepMachine.route_step_id == step.id).delete(
        synchronize_session="fetch"
    )
    seen: set[int] = set()
    new_machines: set[str] = set()
    for raw_code in machine_codes or []:
        if not raw_code or not str(raw_code).strip():
            continue
        cleaned_code = str(raw_code).strip()
        machine = _get_or_create_machine(
            db,
            cleaned_code,
            warehouse_id=warehouse_id,
        )
        if machine.id in seen:
            continue
        seen.add(machine.id)
        new_machines.add(cleaned_code)
        db.add(
            RouteStepMachine(
                route_step_id=step.id,
                machine_id=machine.id,
            )
        )
    db.flush()

    linked = new_machines - old_machines
    unlinked = old_machines - new_machines
    log.info(
        "RouteStep %s machine assignment: step_number=%s, linked=%s, unlinked=%s, total=%s",
        step.id,
        step.step_number,
        sorted(linked),
        sorted(unlinked),
        sorted(new_machines),
        extra={
            "route_step_id": step.id,
            "step_number": step.step_number,
            "linked_machines": sorted(linked),
            "unlinked_machines": sorted(unlinked),
            "assigned_machines": sorted(new_machines),
        },
    )


def list_routes(
    db: Session,
    item_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> list[ProductionRouteResponse]:
    query = db.query(ProductionRoute).options(
        joinedload(ProductionRoute.item),
        joinedload(ProductionRoute.steps)
        .selectinload(RouteStep.allowed_machine_links)
        .joinedload(RouteStepMachine.machine),
    )
    if item_id is not None:
        query = query.filter(ProductionRoute.item_id == item_id)
    if is_active is not None:
        query = query.filter(ProductionRoute.is_active == is_active)

    routes = query.order_by(ProductionRoute.item_id.asc(), ProductionRoute.version.desc()).all()
    return [_to_route_response(r, include_steps=False) for r in routes]


def get_route_detail(db: Session, route_id: int) -> ProductionRouteDetailResponse:
    route = (
        db.query(ProductionRoute)
        .options(
            joinedload(ProductionRoute.item),
            joinedload(ProductionRoute.steps)
            .selectinload(RouteStep.allowed_machine_links)
            .joinedload(RouteStepMachine.machine),
        )
        .filter(ProductionRoute.id == route_id)
        .first()
    )
    if not route:
        raise ValueError(f"Không tìm thấy quy trình sản xuất ID={route_id}")
    return _to_route_response(route, include_steps=True)


def create_route(db: Session, payload: ProductionRouteCreate) -> ProductionRouteDetailResponse:
    existing = (
        db.query(ProductionRoute)
        .filter(ProductionRoute.route_code == payload.route_code.strip())
        .first()
    )
    if existing:
        log.warning(
            "Route create rejected: route_code '%s' already exists",
            payload.route_code.strip(),
            extra={
                "route_code": payload.route_code.strip(),
                "route_name": payload.route_name,
                "item_id": payload.item_id,
                "reason": "route_code_already_exists",
            },
        )
        raise ValueError(f"Mã quy trình '{payload.route_code}' đã tồn tại.")

    item = db.query(Item).filter(Item.id == payload.item_id).first()
    if not item:
        log.warning(
            "Route create rejected: item_id %s not found",
            payload.item_id,
            extra={
                "route_code": payload.route_code.strip(),
                "item_id": payload.item_id,
                "reason": "item_not_found",
            },
        )
        raise ValueError(f"Không tìm thấy sản phẩm (Item ID={payload.item_id}).")

    if payload.is_active:
        reason_code, detail_msg, extra_info = _find_blocking_cnc_wip_or_request(db, payload.item_id)
        if reason_code:
            log.warning(
                "Route create rejected: cannot activate new route '%s' for item_id %s (%s)",
                payload.route_code.strip(),
                payload.item_id,
                detail_msg,
                extra={
                    "route_code": payload.route_code.strip(),
                    "item_id": payload.item_id,
                    **extra_info,
                },
            )
            raise ValueError(
                f"Không thể kích hoạt quy trình mới vì hiện {detail_msg}."
            )
        db.query(ProductionRoute).filter(
            ProductionRoute.item_id == payload.item_id,
            ProductionRoute.is_active.is_(True),
        ).update({"is_active": False})

    route = ProductionRoute(
        route_code=payload.route_code.strip(),
        route_name=payload.route_name.strip(),
        item_id=payload.item_id,
        version=payload.version,
        is_active=payload.is_active,
    )
    db.add(route)
    db.flush()

    total_steps = len(payload.steps)
    for idx, step_data in enumerate(payload.steps):
        step_num = step_data.step_number or (idx + 1)
        step = RouteStep(
            route_id=route.id,
            step_number=step_num,
            stage_level=step_data.stage_level or step_num,
            step_name=step_data.step_name.strip(),
            is_final_cnc_step=(
                step_data.is_final_cnc_step
                if step_data.is_final_cnc_step is not None
                else (idx == total_steps - 1)
            ),
        )
        db.add(step)
        db.flush()
        _sync_step_machines(
            db,
            step,
            step_data.allowed_machines,
            warehouse_id=item.warehouse_id,
        )

    db.commit()
    log.info(
        "Route created: id=%s, route_code=%s, route_name=%s, item_id=%s, version=%s, is_active=%s, steps_count=%s",
        route.id,
        route.route_code,
        route.route_name,
        route.item_id,
        route.version,
        route.is_active,
        total_steps,
        extra={
            "route_id": route.id,
            "route_code": route.route_code,
            "route_name": route.route_name,
            "item_id": route.item_id,
            "version": route.version,
            "is_active": route.is_active,
            "steps_count": total_steps,
        },
    )
    return get_route_detail(db, route.id)


def update_route(
    db: Session, route_id: int, payload: ProductionRouteUpdate
) -> ProductionRouteDetailResponse:
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        log.warning(
            "Route update rejected: route ID %s not found",
            route_id,
            extra={"route_id": route_id, "payload": payload.model_dump(exclude_unset=True), "reason": "route_not_found"},
        )
        raise ValueError(f"Không tìm thấy quy trình sản xuất ID={route_id}")

    item = db.query(Item).filter(Item.id == route.item_id).first()
    warehouse_id = item.warehouse_id if item else None

    old_active = route.is_active
    if payload.route_name is not None:
        route.route_name = payload.route_name.strip()
    if payload.version is not None:
        route.version = payload.version

    if payload.is_active is not None:
        # Trường hợp 1: Tắt kích hoạt quy trình đang active -> CẤM nếu đang có hàng tại CNC hoặc đang vận chuyển
        if payload.is_active is False and route.is_active is True:
            reason_code, detail_msg, extra_info = _find_blocking_cnc_wip_or_request(db, route.item_id)
            if reason_code:
                log.warning(
                    "Route update rejected: cannot deactivate route %s (%s) (%s)",
                    route.id,
                    route.route_code,
                    detail_msg,
                    extra={
                        "route_id": route.id,
                        "route_code": route.route_code,
                        **extra_info,
                    },
                )
                raise ValueError(
                    f"Không thể tắt kích hoạt quy trình '{route.route_name}' ({route.route_code}) "
                    f"vì hiện {detail_msg}."
                )
            route.is_active = False

        # Trường hợp 2: Bật kích hoạt quy trình khác -> CẤM nếu đang có hàng tại CNC hoặc đang vận chuyển
        elif payload.is_active is True and not route.is_active:
            reason_code, detail_msg, extra_info = _find_blocking_cnc_wip_or_request(db, route.item_id)
            if reason_code:
                log.warning(
                    "Route update rejected: cannot activate route %s (%s) (%s)",
                    route.id,
                    route.route_code,
                    detail_msg,
                    extra={
                        "route_id": route.id,
                        "route_code": route.route_code,
                        **extra_info,
                    },
                )
                raise ValueError(
                    f"Không thể kích hoạt quy trình '{route.route_name}' ({route.route_code}) "
                    f"thay thế quy trình hiện tại vì {detail_msg}."
                )
            db.query(ProductionRoute).filter(
                ProductionRoute.item_id == route.item_id,
                ProductionRoute.id != route.id,
                ProductionRoute.is_active.is_(True),
            ).update({"is_active": False})
            route.is_active = True

    if payload.steps is not None:
        if len(payload.steps) == 0:
            log.warning(
                "Route update rejected: empty steps for route %s (%s)",
                route.id,
                route.route_code,
                extra={"route_id": route.id, "route_code": route.route_code, "reason": "empty_steps"},
            )
            raise ValueError("Quy trình sản xuất phải có ít nhất 1 bước công đoạn.")

        # Nếu quy trình đang active, chặn sửa bước công đoạn khi đang có xe tại CNC hoặc đang có lệnh vận chuyển
        if route.is_active:
            reason_code, detail_msg, extra_info = _find_blocking_cnc_wip_or_request(db, route.item_id)
            if reason_code:
                log.warning(
                    "Route steps update rejected for active route %s (%s) (%s)",
                    route.id,
                    route.route_code,
                    detail_msg,
                    extra={
                        "route_id": route.id,
                        "route_code": route.route_code,
                        **extra_info,
                    },
                )
                raise ValueError(
                    f"Không thể thay đổi các bước công đoạn của quy trình '{route.route_name}' ({route.route_code}) "
                    f"vì hiện {detail_msg}."
                )

        db.query(RouteStep).filter(RouteStep.route_id == route.id).delete(
            synchronize_session="fetch"
        )
        db.flush()
        db.expire(route, ["steps"])

        total_steps = len(payload.steps)
        for idx, step_data in enumerate(payload.steps):
            step_num = step_data.step_number or (idx + 1)
            step = RouteStep(
                route_id=route.id,
                step_number=step_num,
                stage_level=step_data.stage_level or step_num,
                step_name=step_data.step_name.strip(),
                is_final_cnc_step=(
                    step_data.is_final_cnc_step
                    if step_data.is_final_cnc_step is not None
                    else (idx == total_steps - 1)
                ),
            )
            db.add(step)
            db.flush()
            _sync_step_machines(
                db,
                step,
                step_data.allowed_machines,
                warehouse_id=warehouse_id,
            )

    db.commit()
    log.info(
        "Route updated: id=%s, route_code=%s, name=%s, version=%s, is_active: %s -> %s",
        route.id,
        route.route_code,
        route.route_name,
        route.version,
        old_active,
        route.is_active,
        extra={
            "route_id": route.id,
            "route_code": route.route_code,
            "route_name": route.route_name,
            "version": route.version,
            "old_active": old_active,
            "is_active": route.is_active,
        },
    )
    return get_route_detail(db, route.id)


def activate_route(db: Session, route_id: int) -> ProductionRouteDetailResponse:
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        log.warning(
            "Route activate rejected: route ID %s not found",
            route_id,
            extra={"route_id": route_id, "reason": "route_not_found"},
        )
        raise ValueError(f"Không tìm thấy quy trình sản xuất ID={route_id}")

    if not route.is_active:
        reason_code, detail_msg, extra_info = _find_blocking_cnc_wip_or_request(db, route.item_id)
        if reason_code:
            log.warning(
                "Route activate rejected: cannot activate route %s (%s) (%s)",
                route.id,
                route.route_code,
                detail_msg,
                extra={
                    "route_id": route.id,
                    "route_code": route.route_code,
                    **extra_info,
                },
            )
            raise ValueError(
                f"Không thể kích hoạt quy trình '{route.route_name}' ({route.route_code}) "
                f"vì hiện {detail_msg}."
            )

        db.query(ProductionRoute).filter(
            ProductionRoute.item_id == route.item_id,
            ProductionRoute.id != route.id,
            ProductionRoute.is_active.is_(True),
        ).update({"is_active": False})

        route.is_active = True
        db.commit()
        log.info(
            "Route activated: id=%s, route_code=%s, is_active: False -> True (reason: manual_activate)",
            route.id,
            route.route_code,
            extra={
                "route_id": route.id,
                "route_code": route.route_code,
                "from_active": False,
                "to_active": True,
                "reason": "manual_activate",
            },
        )
    return get_route_detail(db, route.id)


def delete_route(db: Session, route_id: int) -> None:
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        log.warning(
            "Route delete rejected: route ID %s not found",
            route_id,
            extra={"route_id": route_id, "reason": "route_not_found"},
        )
        raise ValueError(f"Không tìm thấy quy trình sản xuất ID={route_id}")

    # Guard: Chỉ chặn xóa nếu sản phẩm đang có xe tại khu CNC hoặc đang có lệnh vận chuyển
    reason_code, detail_msg, extra_info = _find_blocking_cnc_wip_or_request(db, route.item_id)
    if reason_code:
        log.warning(
            "Route delete rejected: cannot delete route %s (%s) (%s)",
            route.id,
            route.route_code,
            detail_msg,
            extra={
                "route_id": route.id,
                "route_code": route.route_code,
                **extra_info,
            },
        )
        raise ValueError(
            f"Không thể xóa quy trình '{route.route_name}' ({route.route_code}) "
            f"vì hiện {detail_msg}."
        )

    route_code = route.route_code
    route_name = route.route_name
    db.delete(route)
    db.commit()
    log.info(
        "Route deleted: id=%s, route_code=%s, name=%s",
        route_id,
        route_code,
        route_name,
        extra={"route_id": route_id, "route_code": route_code, "route_name": route_name},
    )
