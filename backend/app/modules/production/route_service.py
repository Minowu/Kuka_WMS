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
    """List physical CNC machines from the 3NF Machine table."""
    machines = (
        db.query(Machine)
        .order_by(Machine.machine_code.asc())
        .all()
    )

    result: list[AvailableMachineResponse] = []
    for m in machines:
        machine_locs = [
            loc
            for loc in (m.locations or [])
            if loc.location_type == "CNC_SLOT"
        ]
        machine_locs.sort(key=lambda x: (x.position_index or 99, x.location_code))
        positions = [loc.location_name or loc.location_code for loc in machine_locs]
        slots = [
            MachineSlotInfo(
                id=loc.id,
                location_code=loc.location_code,
                location_name=loc.location_name,
                position_index=loc.position_index,
                node_label=loc.location_label or loc.location_name,
                map_x=loc.map_x,
                map_y=loc.map_y,
                is_active=loc.is_active,
            )
            for loc in machine_locs
        ]
        result.append(
            AvailableMachineResponse(
                id=m.id,
                machine_code=m.machine_code,
                machine_name=m.machine_name,
                warehouse_id=m.warehouse_id,
                is_active=True,
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
            node_label=loc.location_label or loc.location_name,
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
        is_active=True,
        location_count=len(slots),
        positions=[s.location_code for s in slots],
        slots=slots,
    )


def create_machine(db: Session, payload: MachineCreateRequest) -> AvailableMachineResponse:
    code = payload.machine_code.strip()


    wh_id = payload.warehouse_id
    if not wh_id:
        wh = db.query(Warehouse).first()
        wh_id = wh.id if wh else None

    existing = db.query(Machine).filter(Machine.machine_code == code).first()
    if existing:
        raise ValueError(f"Máy CNC với mã '{code}' đã tồn tại trong hệ thống")
    m = Machine(
        machine_code=code,
        machine_name=payload.machine_name or f"Máy {code}",
        warehouse_id=wh_id,
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
        node_lbl = (s_def.node_label or "").strip()
        loc_name = s_def.location_name or f"{m.machine_name} - Vị trí {pos}"
        
        # Tim node goc tu ban do (theo location_label hoac location_code)
        loc = None
        if node_lbl:
            loc = db.query(Location).filter(
                Location.warehouse_id == wh_id,
                (Location.location_label == node_lbl) | (Location.location_name == node_lbl),
            ).first()
        if not loc and s_def.location_code:
            loc = db.query(Location).filter(
                Location.warehouse_id == wh_id,
                Location.location_code == s_def.location_code.strip(),
            ).first()
            
        if not loc:
            raise ValueError(f"Không tìm thấy node bản đồ '{node_lbl or s_def.location_code}' cho Vị trí {pos} của máy {code}")
            
        if loc.location_type != "UNASSIGNED" and (loc.location_type != "CNC_SLOT" or loc.machine_id != m.id):
            raise ValueError(f"Node {loc.location_label or loc.location_code} đã được gán cho {loc.location_type} ({loc.location_name}). Không thể gán cho máy CNC!")
            
        loc.machine_id = m.id
        loc.position_index = pos
        loc.location_type = "CNC_SLOT"
        loc.location_name = loc_name
        if node_lbl and not loc.location_label:
            loc.location_label = node_lbl
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
            node_label=loc.location_label or loc.location_name,
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
        is_active=True,
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

    if payload.slots is not None:
        positions_requested = {s.position_index: s for s in payload.slots}
        for pos, s_def in positions_requested.items():
            if pos < 1 or pos > 3:
                raise ValueError(f"Vị trí đỗ position_index phải từ 1 đến 3 (nhận được: {pos})")
            node_lbl = (s_def.node_label or "").strip()
            loc_name = s_def.location_name or f"{m.machine_name} - Vị trí {pos}"
            
            loc = None
            if node_lbl:
                loc = db.query(Location).filter(
                    Location.warehouse_id == m.warehouse_id,
                    (Location.location_label == node_lbl) | (Location.location_name == node_lbl),
                ).first()
            if not loc and s_def.location_code:
                loc = db.query(Location).filter(
                    Location.warehouse_id == m.warehouse_id,
                    Location.location_code == s_def.location_code.strip(),
                ).first()
                
            if not loc:
                loc = db.query(Location).filter(Location.machine_id == m.id, Location.position_index == pos).first()
                
            if loc:
                if loc.location_type != "UNASSIGNED" and (loc.location_type != "CNC_SLOT" or loc.machine_id != m.id):
                    raise ValueError(f"Node {loc.location_label or loc.location_code} đã được gán cho {loc.location_type} ({loc.location_name}).")
                loc.machine_id = m.id
                loc.position_index = pos
                loc.location_type = "CNC_SLOT"
                loc.location_name = loc_name
                if node_lbl and not loc.location_label:
                    loc.location_label = node_lbl
                if s_def.map_x is not None:
                    loc.map_x = s_def.map_x
                if s_def.map_y is not None:
                    loc.map_y = s_def.map_y
                loc.is_active = True

        for loc in (m.locations or []):
            if loc.position_index not in positions_requested:
                loc.machine_id = None
                loc.position_index = None
                loc.location_type = "UNASSIGNED"
                loc.location_name = loc.location_label or str(loc.id)

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
            node_label=loc.location_label or loc.location_name,
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
        is_active=True,
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
        loc.machine_id = None
        loc.position_index = None
        loc.location_type = "UNASSIGNED"
        loc.location_name = loc.location_label or str(loc.id)
        loc.is_active = True

    # Clean up any route step associations before deleting machine
    db.query(RouteStepMachine).filter(RouteStepMachine.machine_id == m.id).delete(synchronize_session=False)

    db.delete(m)
    db.commit()
    return True


def get_station_catalog(db: Session) -> StationCatalogResponse:
    machines = (
        db.query(Machine)
        .order_by(Machine.machine_code.asc())
        .all()
    )

    machine_groups: list[MachineCatalogGroup] = []
    for m in machines:
        slots = [
            StationCatalogItem(
                id=loc.id,
                location_code=loc.location_code,
                location_label=loc.location_label,
                location_name=loc.location_name,
                location_type=loc.location_type or "CNC_SLOT",
                machine_code=m.machine_code,
                position_index=loc.position_index,
                node_label=loc.location_label or loc.location_name,
                map_x=loc.map_x,
                map_y=loc.map_y,
                is_active=loc.is_active,
            )
            for loc in (m.locations or [])
            if loc.location_type == "CNC_SLOT"
        ]
        slots.sort(key=lambda x: (x.position_index or 99, x.location_code))
        machine_groups.append(
            MachineCatalogGroup(
                id=m.id,
                machine_code=m.machine_code,
                machine_name=m.machine_name,
                is_active=True,
                slots=slots,
            )
        )

    def _query_catalog_items(loc_type: str) -> list[StationCatalogItem]:
        locs = (
            db.query(Location)
            .filter(Location.location_type == loc_type)
            .order_by(Location.position_index.asc().nullslast(), Location.location_code.asc())
            .all()
        )
        return [
            StationCatalogItem(
                id=loc.id,
                location_code=loc.location_code,
                location_label=loc.location_label,
                location_name=loc.location_name,
                location_type=loc.location_type or loc_type,
                machine_code=loc.machine_code,
                position_index=loc.position_index,
                node_label=loc.location_label or loc.location_name,
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
    )


def create_station_slot(
    db: Session,
    loc_type: str,
    payload: StationSlotCreateRequest,
) -> StationCatalogItem:
    wh = db.query(Warehouse).first()
    wh_id = wh.id if wh else 1

    node_lbl = (payload.node_label or "").strip()
    req_code = (payload.location_code or "").strip()
    custom_name = (payload.location_name or "").strip()

    # Tim node da duoc import tu Map (theo node_label hoac location_code)
    loc = None
    if node_lbl:
        loc = db.query(Location).filter(
            Location.warehouse_id == wh_id,
            (Location.location_label == node_lbl) | (Location.location_name == node_lbl),
        ).first()
    if not loc and req_code:
        loc = db.query(Location).filter(
            Location.warehouse_id == wh_id,
            Location.location_code == req_code,
        ).first()

    if not loc:
        raise ValueError(f"Không tìm thấy node bản đồ '{node_lbl or req_code}' để gán trạm.")

    if loc.location_type != "UNASSIGNED" and loc.location_type != loc_type:
        raise ValueError(
            f"Node {loc.location_label or loc.location_code} đã được gán cho khu vực {loc.location_type} ({loc.location_name}). Không thể gán trùng!"
        )

    # Chi UPDATE trang thai va ten nghiep vu, GIU NGUYEN location_code (UUID) va location_label!
    loc.location_type = loc_type
    loc.location_name = custom_name or loc.location_name or loc.location_label or str(loc.id)
    if node_lbl and not loc.location_label:
        loc.location_label = node_lbl
    if payload.position_index is not None:
        loc.position_index = payload.position_index
    if payload.map_x is not None:
        loc.map_x = payload.map_x
    if payload.map_y is not None:
        loc.map_y = payload.map_y
    loc.is_active = True

    db.commit()
    db.refresh(loc)
    return StationCatalogItem(
        id=loc.id,
        location_code=loc.location_code,
        location_label=loc.location_label,
        location_name=loc.location_name,
        location_type=loc.location_type,
        position_index=loc.position_index,
        node_label=loc.location_label or loc.location_name,
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
        loc.location_label = payload.node_label.strip()
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
        location_label=loc.location_label,
        node_label=loc.location_label or loc.location_name,
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
        raise ValueError(f"Không thể giải phóng vị trí {loc.location_name or loc.location_code} đang có phôi hoặc xe đỗ.")

    # Reset vi tri ve UNASSIGNED, tra lai ten mac dinh la nodeLabel
    loc.location_type = "UNASSIGNED"
    loc.location_name = loc.location_label or str(loc.id)
    loc.machine_id = None
    loc.position_index = None
    loc.is_active = True
    db.commit()
    return True


def get_available_map_nodes(
    db: Session,
    only_functional: bool = True,
    rack_only: bool = True,
) -> list[MapAvailableNodeResponse]:
    """
    List map nodes from the `location` table (populated when the real KUKA map is
    imported) and compute their assignment status.

    Per production rule:
    Only the 16 rack nodes (functionType == 2) are used for operational station configuration
    (Raw Materials, CNC slots, Washing slots, Empty Buffers).
    Charging (3), device (4), docking (10) are handled by Fleet Manager.
    """
    query = db.query(Location).filter(Location.is_active.is_(True))
    if rack_only:
        query = query.filter(Location.function_type == 2)
    elif only_functional:
        query = query.filter(Location.function_type.isnot(None))

    results: list[MapAvailableNodeResponse] = []
    for loc in query.all():
        node_lbl = str(loc.location_label or loc.location_name or loc.id)
        # Location khong luu nodeNumber; nodeLabel cua KUKA thuong la so nen dung lam node_number
        node_num = int(node_lbl) if node_lbl.isdigit() else 0

        # Node duoc coi la da gan neu location_type != 'UNASSIGNED'
        is_assigned = loc.location_type != "UNASSIGNED"
        assigned_to = f"{loc.location_type}: {loc.location_name}" if is_assigned else None

        results.append(
            MapAvailableNodeResponse(
                node_number=node_num,
                node_label=node_lbl,
                map_x=loc.map_x or 0,
                map_y=loc.map_y or 0,
                function_type=loc.function_type,
                is_assigned=is_assigned,
                assigned_to=assigned_to,
            )
        )

    results.sort(key=lambda item: (item.node_number, item.node_label))
    return results

