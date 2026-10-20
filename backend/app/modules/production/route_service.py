"""Service layer for managing Production Routes, Route Steps, and CNC Machines (3NF)."""

import json
from pathlib import Path
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
    MachineCatalogGroup,
    MachineCreateRequest,
    MachineSlotCreate,
    MachineSlotInfo,
    MachineUpdateRequest,
    MapAvailableNodeResponse,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
    RouteStepResponse,
    StationCatalogItem,
    StationCatalogResponse,
    StationSlotCreateRequest,
    StationSlotUpdateRequest,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse


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
            is_active=True,
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
        positions = [loc.location_name or loc.location_code for loc in active_locs]
        slots = [
            MachineSlotInfo(
                id=loc.id,
                location_code=loc.location_code,
                location_name=loc.location_name,
                position_index=loc.position_index,
                node_label=loc.location_name,
                map_x=loc.map_x,
                map_y=loc.map_y,
                is_active=loc.is_active,
            )
            for loc in active_locs
        ]
        result.append(
            AvailableMachineResponse(
                id=m.id,
                machine_code=m.machine_code,
                machine_name=m.machine_name,
                warehouse_id=m.warehouse_id,
                is_active=m.is_active,
                location_count=len(positions),
                positions=positions,
                slots=slots,
            )
        )
    return result


def get_machine(db: Session, machine_id: int) -> AvailableMachineResponse:
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise ValueError(f"Không tìm thấy máy CNC với ID {machine_id}")

    active_locs = [
        loc
        for loc in (m.locations or [])
        if loc.is_active and loc.location_type == "CNC_SLOT"
    ]
    active_locs.sort(key=lambda x: (x.position_index or 99, x.location_code))
    slots = [
        MachineSlotInfo(
            id=loc.id,
            location_code=loc.location_code,
            location_name=loc.location_name,
            position_index=loc.position_index,
            node_label=loc.location_name,
            map_x=loc.map_x,
            map_y=loc.map_y,
            is_active=loc.is_active,
        )
        for loc in active_locs
    ]
    return AvailableMachineResponse(
        id=m.id,
        machine_code=m.machine_code,
        machine_name=m.machine_name,
        warehouse_id=m.warehouse_id,
        is_active=m.is_active,
        location_count=len(slots),
        positions=[s.location_code for s in slots],
        slots=slots,
    )


def create_machine(db: Session, payload: MachineCreateRequest) -> AvailableMachineResponse:
    code = payload.machine_code.strip()
    existing = db.query(Machine).filter(Machine.machine_code == code).first()
    if existing:
        raise ValueError(f"Máy CNC với mã '{code}' đã tồn tại trong hệ thống")

    wh_id = payload.warehouse_id
    if not wh_id:
        wh = db.query(Warehouse).first()
        wh_id = wh.id if wh else None

    m = Machine(
        machine_code=code,
        machine_name=payload.machine_name or f"Máy {code}",
        warehouse_id=wh_id,
        is_active=True,
    )
    db.add(m)
    db.flush()

    # Hỗ trợ máy CNC linh hoạt từ 1 đến 3 vị trí đỗ (POS1, POS2, POS3)
    slot_defs = payload.slots
    if not slot_defs:
        slot_defs = [
            MachineSlotCreate(position_index=1),
            MachineSlotCreate(position_index=2),
        ]

    for s_def in slot_defs:
        pos = s_def.position_index
        if pos < 1 or pos > 3:
            raise ValueError(f"Vị trí đỗ position_index phải từ 1 đến 3 (nhận được: {pos})")
        loc_code = s_def.location_code or f"{code}-POS{pos}"
        loc_name = s_def.location_name or f"{m.machine_name} - Vị trí {pos}"
        loc = db.query(Location).filter(
            Location.warehouse_id == wh_id,
            Location.location_code == loc_code,
        ).first()
        if not loc:
            loc = Location(
                location_code=loc_code,
                location_name=s_def.node_label or loc_name,
                location_type="CNC_SLOT",
                machine_id=m.id,
                position_index=pos,
                map_x=s_def.map_x,
                map_y=s_def.map_y,
                warehouse_id=wh_id,
                is_active=True,
            )
            db.add(loc)
        else:
            loc.machine_id = m.id
            loc.machine_code = m.machine_code
            loc.position_index = pos
            if s_def.location_name:
                loc.location_name = s_def.location_name
            if s_def.node_label is not None:
                loc.location_name = s_def.node_label
            if s_def.map_x is not None:
                loc.map_x = s_def.map_x
            if s_def.map_y is not None:
                loc.map_y = s_def.map_y
            loc.is_active = True

    db.commit()
    db.refresh(m)

    slots = [
        MachineSlotInfo(
            id=loc.id,
            location_code=loc.location_code,
            location_name=loc.location_name,
            position_index=loc.position_index,
            node_label=loc.location_name,
            map_x=loc.map_x,
            map_y=loc.map_y,
            is_active=loc.is_active,
        )
        for loc in (m.locations or [])
        if loc.is_active and loc.location_type == "CNC_SLOT"
    ]
    slots.sort(key=lambda s: s.position_index or 99)

    return AvailableMachineResponse(
        id=m.id,
        machine_code=m.machine_code,
        machine_name=m.machine_name,
        warehouse_id=m.warehouse_id,
        is_active=m.is_active,
        location_count=len(slots),
        positions=[s.location_code for s in slots],
        slots=slots,
    )


def update_machine(db: Session, machine_id: int, payload: MachineUpdateRequest) -> AvailableMachineResponse:
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise ValueError(f"Không tìm thấy máy CNC với ID {machine_id}")

    if payload.machine_name is not None:
        m.machine_name = payload.machine_name.strip()
    if payload.is_active is not None:
        m.is_active = payload.is_active

    if payload.slots is not None:
        positions_requested = {s.position_index: s for s in payload.slots}
        for pos, s_def in positions_requested.items():
            if pos < 1 or pos > 3:
                raise ValueError(f"Vị trí đỗ position_index phải từ 1 đến 3 (nhận được: {pos})")
            loc_code = s_def.location_code or f"{m.machine_code}-POS{pos}"
            loc = (
                db.query(Location)
                .filter(
                    Location.machine_id == m.id,
                    Location.position_index == pos,
                )
                .first()
            )
            if not loc:
                loc = db.query(Location).filter(Location.location_code == loc_code).first()
            if not loc:
                loc = Location(
                    location_code=loc_code,
                    location_name=s_def.node_label or s_def.location_name or f"{m.machine_name} - Vị trí {pos}",
                    location_type="CNC_SLOT",
                    machine_id=m.id,
                    position_index=pos,
                    map_x=s_def.map_x,
                    map_y=s_def.map_y,
                    warehouse_id=m.warehouse_id,
                    is_active=True,
                )
                db.add(loc)
            else:
                loc.machine_id = m.id
                loc.machine_code = m.machine_code
                loc.position_index = pos
                if s_def.location_name:
                    loc.location_name = s_def.location_name
                if s_def.node_label is not None:
                    loc.location_name = s_def.node_label
                if s_def.map_x is not None:
                    loc.map_x = s_def.map_x
                if s_def.map_y is not None:
                    loc.map_y = s_def.map_y
                loc.is_active = True

        for loc in (m.locations or []):
            if loc.position_index not in positions_requested:
                loc.is_active = False

    db.commit()
    db.refresh(m)

    active_locs = [
        loc
        for loc in (m.locations or [])
        if loc.is_active and loc.location_type == "CNC_SLOT"
    ]
    active_locs.sort(key=lambda x: (x.position_index or 99, x.location_code))
    slots = [
        MachineSlotInfo(
            id=loc.id,
            location_code=loc.location_code,
            location_name=loc.location_name,
            position_index=loc.position_index,
            node_label=loc.location_name,
            map_x=loc.map_x,
            map_y=loc.map_y,
            is_active=loc.is_active,
        )
        for loc in active_locs
    ]

    return AvailableMachineResponse(
        id=m.id,
        machine_code=m.machine_code,
        machine_name=m.machine_name,
        warehouse_id=m.warehouse_id,
        is_active=m.is_active,
        location_count=len(slots),
        positions=[s.location_code for s in slots],
        slots=slots,
    )


def delete_machine(db: Session, machine_id: int) -> bool:
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise ValueError(f"Không tìm thấy máy CNC với ID {machine_id}")

    slot_ids = [loc.id for loc in (m.locations or [])]
    if slot_ids:
        active_stocks = (
            db.query(ItemStock)
            .filter(
                ItemStock.location_id.in_(slot_ids),
                ItemStock.is_active.is_(True),
            )
            .count()
        )
        if active_stocks > 0:
            raise ValueError(f"Không thể xóa máy CNC {m.machine_code} đang có phôi hoặc xe đỗ tại vị trí.")

    for loc in (m.locations or []):
        loc.is_active = False
    m.is_active = False
    db.commit()
    return True


def get_station_catalog(db: Session) -> StationCatalogResponse:
    machines = (
        db.query(Machine)
        .filter(Machine.is_active.is_(True))
        .order_by(Machine.machine_code.asc())
        .all()
    )

    machine_groups: list[MachineCatalogGroup] = []
    for m in machines:
        slots = [
            StationCatalogItem(
                id=loc.id,
                location_code=loc.location_code,
                location_name=loc.location_name,
                location_type=loc.location_type or "CNC_SLOT",
                machine_code=m.machine_code,
                position_index=loc.position_index,
                node_label=loc.location_name,
                map_x=loc.map_x,
                map_y=loc.map_y,
                is_active=loc.is_active,
            )
            for loc in (m.locations or [])
            if loc.is_active and loc.location_type == "CNC_SLOT"
        ]
        slots.sort(key=lambda x: (x.position_index or 99, x.location_code))
        machine_groups.append(
            MachineCatalogGroup(
                id=m.id,
                machine_code=m.machine_code,
                machine_name=m.machine_name,
                is_active=m.is_active,
                slots=slots,
            )
        )

    def _query_catalog_items(loc_type: str) -> list[StationCatalogItem]:
        locs = (
            db.query(Location)
            .filter(Location.location_type == loc_type, Location.is_active.is_(True))
            .order_by(Location.position_index.asc().nullslast(), Location.location_code.asc())
            .all()
        )
        return [
            StationCatalogItem(
                id=loc.id,
                location_code=loc.location_code,
                location_name=loc.location_name,
                location_type=loc.location_type or loc_type,
                machine_code=loc.machine_code,
                position_index=loc.position_index,
                node_label=loc.location_name,
                map_x=loc.map_x,
                map_y=loc.map_y,
                is_active=loc.is_active,
            )
            for loc in locs
        ]

    raw_mats = _query_catalog_items("RAW_MATERIAL")
    wash_slots = _query_catalog_items("WASHING_SLOT")
    buf_slots = _query_catalog_items("EMPTY_CART_BUFFER")

    return StationCatalogResponse(
        raw_materials=raw_mats,
        washing_slots=wash_slots,
        empty_buffers=buf_slots,
        machines=machine_groups,
        buffer_slots=buf_slots,
    )


def create_station_slot(
    db: Session,
    loc_type: str,
    payload: StationSlotCreateRequest,
) -> StationCatalogItem:
    code = payload.location_code.strip()
    wh = db.query(Warehouse).first()
    wh_id = wh.id if wh else 1

    existing = db.query(Location).filter(
        Location.warehouse_id == wh_id,
        Location.location_code == code,
    ).first()
    if existing and existing.is_active:
        raise ValueError(f"Vị trí với mã '{code}' đã tồn tại trong hệ thống")

    if not existing:
        loc = Location(
            location_code=code,
            location_name=payload.node_label or payload.location_name or code,
            location_type=loc_type,
            position_index=payload.position_index,
            map_x=payload.map_x,
            map_y=payload.map_y,
            warehouse_id=wh_id,
            is_active=True,
        )
        db.add(loc)
    else:
        loc = existing
        loc.location_name = payload.location_name or loc.location_name
        loc.location_type = loc_type
        loc.position_index = payload.position_index
        loc.location_name = payload.node_label or loc.location_name
        loc.map_x = payload.map_x
        loc.map_y = payload.map_y
        loc.is_active = True

    db.commit()
    db.refresh(loc)
    return StationCatalogItem(
        id=loc.id,
        location_code=loc.location_code,
        location_name=loc.location_name,
        location_type=loc.location_type,
        position_index=loc.position_index,
        node_label=loc.location_name,
        map_x=loc.map_x,
        map_y=loc.map_y,
        is_active=loc.is_active,
    )


def update_station_slot(
    db: Session,
    location_id: int,
    payload: StationSlotUpdateRequest,
) -> StationCatalogItem:
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise ValueError(f"Không tìm thấy vị trí với ID {location_id}")

    if payload.location_name is not None:
        loc.location_name = payload.location_name.strip()
    if payload.position_index is not None:
        loc.position_index = payload.position_index
    if payload.node_label is not None:
        loc.location_name = payload.node_label or loc.location_name.strip()
    if payload.map_x is not None:
        loc.map_x = payload.map_x
    if payload.map_y is not None:
        loc.map_y = payload.map_y
    if payload.is_active is not None:
        loc.is_active = payload.is_active

    db.commit()
    db.refresh(loc)
    return StationCatalogItem(
        id=loc.id,
        location_code=loc.location_code,
        location_name=loc.location_name,
        location_type=loc.location_type,
        position_index=loc.position_index,
        node_label=loc.location_name,
        map_x=loc.map_x,
        map_y=loc.map_y,
        is_active=loc.is_active,
    )


def delete_station_slot(db: Session, location_id: int) -> bool:
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise ValueError(f"Không tìm thấy vị trí với ID {location_id}")

    active_stocks = (
        db.query(ItemStock)
        .filter(ItemStock.location_id == loc.id, ItemStock.is_active.is_(True))
        .count()
    )
    if active_stocks > 0:
        raise ValueError(f"Không thể xóa vị trí {loc.location_code} đang có phôi hoặc xe đỗ.")

    loc.is_active = False
    db.commit()
    return True


def get_available_map_nodes(
    db: Session,
    only_functional: bool = True,
    rack_only: bool = True,
) -> list[MapAvailableNodeResponse]:
    """
    Parse nodes from map_CNC001_CNC001_28s.json and compute availability
    against active locations in database.

    Per production rule:
    Only the 16 rack nodes (functionType == 2) are used for operational station configuration
    (Raw Materials, CNC slots, Washing slots, Empty Buffers).
    Charging (3), device (4), docking (10) are handled by Fleet Manager.
    """
    backend_dir = Path(__file__).resolve().parents[3]
    candidate_paths = [
        backend_dir.parent / "map_CNC001_CNC001_28s.json",
        backend_dir / "map_CNC001_CNC001_28s.json",
    ]
    map_path = None
    for p in candidate_paths:
        if p.is_file():
            map_path = p
            break

    if not map_path:
        raise ValueError("Không tìm thấy file bản đồ xưởng map_CNC001_CNC001_28s.json")

    with open(map_path, "r", encoding="utf-8") as f:
        map_data = json.load(f)

    floor_list = map_data.get("floorList", [])
    if not floor_list:
        return []

    node_list = floor_list[0].get("nodeList", [])

    locations = db.query(Location).filter(Location.is_active.is_(True)).all()
    assigned_by_label = {
        str(loc.location_name): loc.location_code
        for loc in locations
        if loc.location_name
    }
    assigned_by_coords = {
        (loc.map_x, loc.map_y): loc.location_code
        for loc in locations
        if loc.map_x is not None and loc.map_y is not None
    }

    results: list[MapAvailableNodeResponse] = []
    for n in node_list:
        func_list = n.get("functionList", [])
        if rack_only:
            # Strictly filter for functionType == 2 (16 Rack/Storage nodes)
            if not any(f.get("functionType") == 2 for f in func_list):
                continue
        elif only_functional and not func_list:
            continue

        node_num = int(n.get("nodeNumber", 0))
        node_lbl = str(n.get("nodeLabel") or node_num)
        mx = round(float(n.get("xCoordinate", 0)) * 1000)
        my = round(float(n.get("yCoordinate", 0)) * 1000)

        function_type = func_list[0].get("functionType") if func_list else None

        assigned_to = assigned_by_label.get(node_lbl) or assigned_by_coords.get((mx, my))
        is_assigned = assigned_to is not None

        results.append(
            MapAvailableNodeResponse(
                node_number=node_num,
                node_label=node_lbl,
                map_x=mx,
                map_y=my,
                function_type=function_type,
                is_assigned=is_assigned,
                assigned_to=assigned_to,
            )
        )

    results.sort(key=lambda item: item.node_number)
    return results

