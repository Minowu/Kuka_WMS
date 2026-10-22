from typing import Optional
from sqlalchemy.orm import Session

from app.modules.production.production_models import Machine, RouteStepMachine
from app.modules.production.machine_schema import (
    AvailableMachineResponse,
    MachineCreateRequest,
    MachineUpdateRequest,
    MachineSlotCreate,
    MachineSlotInfo,
)
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse


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
        if not wh:
            raise ValueError("Hệ thống chưa khởi tạo dữ liệu Nhà kho (Warehouse). Vui lòng tạo kho trước.")
        wh_id = wh.id

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
        
        loc = None
        if node_lbl:
            loc = db.query(Location).filter(
                Location.warehouse_id == wh_id,
                (Location.location_label == node_lbl)
                | (Location.location_name == node_lbl)
                | (Location.location_code == node_lbl),
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
