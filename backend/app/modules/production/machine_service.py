from sqlalchemy.orm import Session

from app.modules.production.production_models import Machine, RouteStepMachine
from app.modules.production.machine_schema import (
    AvailableMachineResponse,
    MachineCreateRequest,
    MachineUpdateRequest,
    MachineSlotCreate,
    MachineSlotInfo,
)
from app.modules.production.location_guard import (
    ensure_location_has_no_stock,
    find_map_node,
    release_location,
    resolve_warehouse_id,
)
from app.modules.warehouse.location_map.location_model import Location


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

    wh_id = resolve_warehouse_id(db, payload.warehouse_id)

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
        
        loc = find_map_node(db, wh_id, node_lbl, s_def.location_code)
        if not loc:
            raise ValueError(f"Không tìm thấy node bản đồ '{node_lbl or s_def.location_code}' cho Vị trí {pos} của máy {code}")

        if loc.location_type != "UNASSIGNED" and (loc.location_type != "CNC_SLOT" or loc.machine_id != m.id):
            raise ValueError(f"Node {loc.location_label or loc.location_code} đã được gán cho {loc.location_type} ({loc.location_name}). Không thể gán cho máy CNC!")
        ensure_location_has_no_stock(db, loc, f"gán Vị trí {pos} cho máy {code}")
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
        if not payload.slots:
            raise ValueError("Máy CNC phải có ít nhất 1 vị trí đỗ.")

        # Chụp trạng thái slot hiện tại TỪ DB (không dùng m.locations vì sẽ bị thay đổi trong vòng lặp)
        old_locs = db.query(Location).filter(Location.machine_id == m.id).all()
        old_by_pos = {loc.position_index: loc for loc in old_locs}

        positions_requested = {s.position_index: s for s in payload.slots}
        kept_ids: set[int] = set()
        used_target_ids: set[int] = set()

        for pos, s_def in positions_requested.items():
            if pos < 1 or pos > 3:
                raise ValueError(f"Vị trí đỗ position_index phải từ 1 đến 3 (nhận được: {pos})")
            node_lbl = (s_def.node_label or "").strip()
            loc_name = s_def.location_name or f"{m.machine_name} - Vị trí {pos}"

            target = find_map_node(db, m.warehouse_id, node_lbl, s_def.location_code)
            if not target:
                # Không gửi node -> giữ nguyên node cũ của POS này
                target = old_by_pos.get(pos)
            if not target:
                raise ValueError(f"Không tìm thấy node bản đồ '{node_lbl or s_def.location_code}' cho Vị trí {pos}.")
            if target.id in used_target_ids:
                raise ValueError(f"Node {target.location_label or target.location_code} bị chọn cho nhiều vị trí đỗ cùng lúc.")
            used_target_ids.add(target.id)

            is_own_slot = target.location_type == "CNC_SLOT" and target.machine_id == m.id
            if target.location_type != "UNASSIGNED" and not is_own_slot:
                raise ValueError(f"Node {target.location_label or target.location_code} đã được gán cho {target.location_type} ({target.location_name}).")

            old = old_by_pos.get(pos)
            if old is not None and old.id != target.id:
                # Đổi node của POS: node cũ không được còn phôi, node mới không được có hàng
                ensure_location_has_no_stock(db, old, f"đổi node của Vị trí {pos}")
            if not is_own_slot:
                ensure_location_has_no_stock(db, target, f"gán node mới cho Vị trí {pos}")

            target.machine_id = m.id
            target.position_index = pos
            target.location_type = "CNC_SLOT"
            target.location_name = loc_name
            target.is_active = True
            kept_ids.add(target.id)

        # Giải phóng mọi node cũ không còn dùng (slot bị bớt HOẶC node cũ của POS vừa đổi)
        for loc in old_locs:
            if loc.id not in kept_ids:
                ensure_location_has_no_stock(db, loc, f"bớt Vị trí {loc.position_index} của máy {m.machine_code}")
                release_location(loc, db)

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

    # Guard: Kiểm tra máy có đang được gán trong bất kỳ công đoạn nào của ProductionRoute không
    step_machine = (
        db.query(RouteStepMachine)
        .filter(RouteStepMachine.machine_id == m.id)
        .first()
    )
    if step_machine:
        step = step_machine.route_step
        route = step.route if step else None
        route_desc = (
            f"'{route.route_name}' ({route.route_code})"
            if route
            else (f"ID={step.route_id}" if step else "N/A")
        )
        step_name = step.step_name if step else f"bước #{step_machine.route_step_id}"
        raise ValueError(
            f"Không thể xóa máy CNC '{m.machine_code}' vì đang được gán cho công đoạn "
            f"'{step_name}' trong quy trình {route_desc}. Vui lòng gỡ máy khỏi quy trình trước khi xóa."
        )

    locations_to_release = list(m.locations or [])
    for loc in locations_to_release:
        ensure_location_has_no_stock(db, loc, f"xóa máy CNC {m.machine_code}")

    for loc in locations_to_release:
        release_location(loc, db)

    db.delete(m)
    db.commit()
    return True
