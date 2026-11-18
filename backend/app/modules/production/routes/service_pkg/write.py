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
from app.modules.production.routes.schema import (
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
from app.modules.production.routes.service_pkg.query import get_route_detail

log = get_logger("wms.domain.production")

ACTIVE_ROUTE_REQUEST_STATUSES = (
    "pending",
    "queued_for_cart",
    "queued_for_slot",
    "in_progress",
)



from app.modules.production.routes.service_pkg.helpers import (
    _find_blocking_cnc_wip_or_request,
    _get_or_create_machine,
    _sync_step_machines,
    _to_route_response,
)

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
