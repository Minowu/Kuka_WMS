"""Service layer for managing Production Routes, Route Steps, and CNC Machines (3NF)."""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.production.production_models import (
    Machine,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
)
from app.modules.production.route_schema import (
    AvailableMachineResponse,
    ItemSummary,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
    RouteStepResponse,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.location_map.location_model import Location


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
    default_stage_level: Optional[int] = None,
) -> Machine:
    code = machine_code.strip()
    machine = db.query(Machine).filter(Machine.machine_code == code).first()
    if machine is None:
        machine = Machine(
            machine_code=code,
            machine_name=f"Máy {code}",
            warehouse_id=warehouse_id,
            default_stage_level=default_stage_level,
            is_active=True,
        )
        db.add(machine)
        db.flush()
    elif default_stage_level is not None and machine.default_stage_level is None:
        machine.default_stage_level = default_stage_level
    return machine


def _sync_step_machines(
    db: Session,
    step: RouteStep,
    machine_codes: list[str],
    warehouse_id: Optional[int] = None,
) -> None:
    """Populate normalized RouteStepMachine join rows for a RouteStep."""
    db.query(RouteStepMachine).filter(RouteStepMachine.route_step_id == step.id).delete(
        synchronize_session=False
    )
    seen: set[int] = set()
    for raw_code in machine_codes or []:
        if not raw_code or not str(raw_code).strip():
            continue
        machine = _get_or_create_machine(
            db,
            str(raw_code).strip(),
            warehouse_id=warehouse_id,
            default_stage_level=step.stage_level,
        )
        if machine.id in seen:
            continue
        seen.add(machine.id)
        db.add(
            RouteStepMachine(
                route_step_id=step.id,
                machine_id=machine.id,
            )
        )
    db.flush()


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
        raise ValueError(f"Mã quy trình '{payload.route_code}' đã tồn tại.")

    item = db.query(Item).filter(Item.id == payload.item_id).first()
    if not item:
        raise ValueError(f"Không tìm thấy sản phẩm (Item ID={payload.item_id}).")

    if payload.is_active:
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

    for idx, step_data in enumerate(payload.steps):
        step = RouteStep(
            route_id=route.id,
            step_number=step_data.step_number or (idx + 1),
            stage_level=step_data.stage_level,
            step_name=step_data.step_name.strip(),
            is_final_cnc_step=step_data.is_final_cnc_step,
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
    return get_route_detail(db, route.id)


def update_route(
    db: Session, route_id: int, payload: ProductionRouteUpdate
) -> ProductionRouteDetailResponse:
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        raise ValueError(f"Không tìm thấy quy trình sản xuất ID={route_id}")

    item = db.query(Item).filter(Item.id == route.item_id).first()
    warehouse_id = item.warehouse_id if item else None

    if payload.route_name is not None:
        route.route_name = payload.route_name.strip()
    if payload.version is not None:
        route.version = payload.version

    if payload.is_active is not None:
        if payload.is_active:
            db.query(ProductionRoute).filter(
                ProductionRoute.item_id == route.item_id,
                ProductionRoute.id != route.id,
                ProductionRoute.is_active.is_(True),
            ).update({"is_active": False})
        route.is_active = payload.is_active

    if payload.steps is not None:
        db.query(RouteStep).filter(RouteStep.route_id == route.id).delete(
            synchronize_session=False
        )
        db.flush()

        for idx, step_data in enumerate(payload.steps):
            step = RouteStep(
                route_id=route.id,
                step_number=step_data.step_number or (idx + 1),
                stage_level=step_data.stage_level,
                step_name=step_data.step_name.strip(),
                is_final_cnc_step=step_data.is_final_cnc_step,
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
    return get_route_detail(db, route.id)


def activate_route(db: Session, route_id: int) -> ProductionRouteDetailResponse:
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        raise ValueError(f"Không tìm thấy quy trình sản xuất ID={route_id}")

    db.query(ProductionRoute).filter(
        ProductionRoute.item_id == route.item_id,
        ProductionRoute.id != route.id,
        ProductionRoute.is_active.is_(True),
    ).update({"is_active": False})

    route.is_active = True
    db.commit()
    return get_route_detail(db, route.id)


def delete_route(db: Session, route_id: int) -> None:
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        raise ValueError(f"Không tìm thấy quy trình sản xuất ID={route_id}")

    db.delete(route)
    db.commit()


def list_available_machines(db: Session) -> list[AvailableMachineResponse]:
    """List physical CNC machines from the 3NF Machine table, syncing any unlinked CNC_SLOT locations."""
    locations = (
        db.query(Location)
        .filter(
            Location.is_active.is_(True),
            Location.location_type == "CNC_SLOT",
            Location.machine_code.isnot(None),
        )
        .order_by(Location.machine_code.asc(), Location.position_index.asc())
        .all()
    )

    dirty = False
    for loc in locations:
        if loc.machine_code and loc.machine_id is None:
            machine = _get_or_create_machine(
                db,
                loc.machine_code,
                warehouse_id=loc.warehouse_id,
                default_stage_level=loc.default_stage_level,
            )
            loc.machine_id = machine.id
            dirty = True
    if dirty:
        db.commit()

    machines = (
        db.query(Machine)
        .filter(Machine.is_active.is_(True))
        .order_by(Machine.machine_code.asc())
        .all()
    )

    result: list[AvailableMachineResponse] = []
    for m in machines:
        active_locs = [
            loc
            for loc in (m.locations or [])
            if loc.is_active and loc.location_type == "CNC_SLOT"
        ]
        active_locs.sort(key=lambda x: (x.position_index or 99, x.location_code))
        positions = [loc.bin_code or loc.location_code for loc in active_locs]
        result.append(
            AvailableMachineResponse(
                id=m.id,
                machine_code=m.machine_code,
                machine_name=m.machine_name,
                default_stage_level=m.default_stage_level,
                location_count=len(positions),
                positions=positions,
            )
        )
    return result
