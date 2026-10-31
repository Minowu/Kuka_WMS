from typing import Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger
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

log = get_logger("wms.domain.production")

VALID_MACHINE_STATUSES = {"IDLE", "RUNNING", "ERROR", "MAINTENANCE"}


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
        log.warning(
            "Machine create rejected: machine_code '%s' already exists",
            code,
            extra={"machine_code": code, "payload": payload.model_dump(), "reason": "machine_code_already_exists"},
        )
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
            log.warning(
                "Machine create rejected: position_index %s out of range [1, 3] for machine '%s'",
                pos,
                code,
                extra={"machine_code": code, "position_index": pos, "reason": "invalid_position_index"},
            )
            raise ValueError(f"Vị trí đỗ position_index phải từ 1 đến 3 (nhận được: {pos})")
        node_lbl = (s_def.node_label or "").strip()
        loc_name = s_def.location_name or f"{m.machine_name} - Vị trí {pos}"
        
        loc = find_map_node(db, wh_id, node_lbl, s_def.location_code)
        if not loc:
            log.warning(
                "Machine create rejected: map node '%s' not found for machine '%s' POS%s",
                node_lbl or s_def.location_code,
                code,
                pos,
                extra={"machine_code": code, "position_index": pos, "node_label": node_lbl, "reason": "node_not_found"},
            )
            raise ValueError(f"Không tìm thấy node bản đồ '{node_lbl or s_def.location_code}' cho Vị trí {pos} của máy {code}")

        if loc.location_type != "UNASSIGNED" and (loc.location_type != "CNC_SLOT" or loc.machine_id != m.id):
            log.warning(
                "Machine create rejected: node %s already assigned to %s (%s)",
                loc.location_label or loc.location_code,
                loc.location_type,
                loc.location_name,
                extra={"machine_code": code, "station_code": loc.location_code, "assigned_type": loc.location_type, "reason": "node_already_assigned"},
            )
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
        log.info(
            "Machine %s assigned to station slot: location_code=%s, position_index=%s, node_label=%s",
            m.machine_code,
            loc.location_code,
            pos,
            node_lbl,
            extra={"machine_code": m.machine_code, "station_code": loc.location_code, "position_index": pos},
        )

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

    log.info(
        "Machine created: id=%s, machine_code=%s, name=%s, warehouse_id=%s, slots_count=%s",
        m.id,
        m.machine_code,
        m.machine_name,
        m.warehouse_id,
        len(slots),
        extra={"machine_code": m.machine_code, "machine_id": m.id, "slots_count": len(slots)},
    )
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
        log.warning(
            "Machine update rejected: machine ID %s not found",
            machine_id,
            extra={"machine_id": machine_id, "reason": "machine_not_found"},
        )
        raise ValueError(f"Không tìm thấy máy CNC với ID {machine_id}")

    if payload.machine_name is not None:
        m.machine_name = payload.machine_name.strip()

    if payload.slots is not None:
        if not payload.slots:
            log.warning(
                "Machine update rejected: slots list cannot be empty for machine %s",
                m.machine_code,
                extra={"machine_code": m.machine_code, "reason": "empty_slots"},
            )
            raise ValueError("Máy CNC phải có ít nhất 1 vị trí đỗ.")

        # Chụp trạng thái slot hiện tại TỪ DB (không dùng m.locations vì sẽ bị thay đổi trong vòng lặp)
        old_locs = db.query(Location).filter(Location.machine_id == m.id).all()
        old_by_pos = {loc.position_index: loc for loc in old_locs}

        positions_requested = {s.position_index: s for s in payload.slots}
        kept_ids: set[int] = set()
        used_target_ids: set[int] = set()

        for pos, s_def in positions_requested.items():
            if pos < 1 or pos > 3:
                log.warning(
                    "Machine update rejected: invalid position_index %s for machine %s",
                    pos,
                    m.machine_code,
                    extra={"machine_code": m.machine_code, "position_index": pos, "reason": "invalid_position_index"},
                )
                raise ValueError(f"Vị trí đỗ position_index phải từ 1 đến 3 (nhận được: {pos})")
            node_lbl = (s_def.node_label or "").strip()
            loc_name = s_def.location_name or f"{m.machine_name} - Vị trí {pos}"

            target = find_map_node(db, m.warehouse_id, node_lbl, s_def.location_code)
            if not target:
                # Không gửi node -> giữ nguyên node cũ của POS này
                target = old_by_pos.get(pos)
            if not target:
                log.warning(
                    "Machine update rejected: map node '%s' not found for machine %s POS%s",
                    node_lbl or s_def.location_code,
                    m.machine_code,
                    pos,
                    extra={"machine_code": m.machine_code, "position_index": pos, "reason": "node_not_found"},
                )
                raise ValueError(f"Không tìm thấy node bản đồ '{node_lbl or s_def.location_code}' cho Vị trí {pos}.")
            if target.id in used_target_ids:
                log.warning(
                    "Machine update rejected: duplicate node %s for machine %s",
                    target.location_code,
                    m.machine_code,
                    extra={"machine_code": m.machine_code, "station_code": target.location_code, "reason": "duplicate_node"},
                )
                raise ValueError(f"Node {target.location_label or target.location_code} bị chọn cho nhiều vị trí đỗ cùng lúc.")
            used_target_ids.add(target.id)

            is_own_slot = target.location_type == "CNC_SLOT" and target.machine_id == m.id
            if target.location_type != "UNASSIGNED" and not is_own_slot:
                log.warning(
                    "Machine update rejected: node %s already assigned to %s (%s)",
                    target.location_code,
                    target.location_type,
                    target.location_name,
                    extra={"machine_code": m.machine_code, "station_code": target.location_code, "assigned_type": target.location_type, "reason": "node_already_assigned"},
                )
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
            log.info(
                "Machine %s slot assigned: location_code=%s, position_index=%s",
                m.machine_code,
                target.location_code,
                pos,
                extra={"machine_code": m.machine_code, "station_code": target.location_code, "position_index": pos},
            )

        # Giải phóng mọi node cũ không còn dùng (slot bị bớt HOẶC node cũ của POS vừa đổi)
        for loc in old_locs:
            if loc.id not in kept_ids:
                ensure_location_has_no_stock(db, loc, f"bớt Vị trí {loc.position_index} của máy {m.machine_code}")
                release_location(loc, db)
                log.info(
                    "Machine %s slot unassigned: location_code=%s, position_index=%s",
                    m.machine_code,
                    loc.location_code,
                    loc.position_index,
                    extra={"machine_code": m.machine_code, "station_code": loc.location_code, "position_index": loc.position_index},
                )

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

    log.info(
        "Machine updated: id=%s, machine_code=%s, name=%s, slots_count=%s",
        m.id,
        m.machine_code,
        m.machine_name,
        len(slots),
        extra={"machine_code": m.machine_code, "machine_id": m.id, "slots_count": len(slots)},
    )
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
        log.warning(
            "Machine delete rejected: machine ID %s not found",
            machine_id,
            extra={"machine_id": machine_id, "reason": "machine_not_found"},
        )
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
        log.warning(
            "Machine delete rejected: machine '%s' assigned to step '%s' in route %s",
            m.machine_code,
            step_name,
            route_desc,
            extra={"machine_code": m.machine_code, "step_name": step_name, "reason": "assigned_to_route_step"},
        )
        raise ValueError(
            f"Không thể xóa máy CNC '{m.machine_code}' vì đang được gán cho công đoạn "
            f"'{step_name}' trong quy trình {route_desc}. Vui lòng gỡ máy khỏi quy trình trước khi xóa."
        )

    locations_to_release = list(m.locations or [])
    for loc in locations_to_release:
        ensure_location_has_no_stock(db, loc, f"xóa máy CNC {m.machine_code}")

    for loc in locations_to_release:
        log.info(
            "Machine %s slot unassigned for deletion: location_code=%s, position_index=%s",
            m.machine_code,
            loc.location_code,
            loc.position_index,
            extra={"machine_code": m.machine_code, "station_code": loc.location_code, "position_index": loc.position_index},
        )
        release_location(loc, db)

    machine_code = m.machine_code
    db.delete(m)
    db.commit()
    log.info(
        "Machine deleted: id=%s, machine_code=%s",
        machine_id,
        machine_code,
        extra={"machine_code": machine_code, "machine_id": machine_id},
    )
    return True


def update_machine_status(
    db: Session,
    machine_id: int,
    new_status: str,
    old_status: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """Update and log CNC machine status transition (IDLE, RUNNING, ERROR, MAINTENANCE)."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        log.warning(
            "Machine status update rejected: machine ID %s not found",
            machine_id,
            extra={"machine_id": machine_id, "target_status": new_status, "reason": "machine_not_found"},
        )
        raise ValueError(f"Không tìm thấy máy CNC với ID {machine_id}")

    target = new_status.upper().strip()
    if target not in VALID_MACHINE_STATUSES:
        log.warning(
            "Machine status update rejected: invalid status '%s' for machine %s (valid: %s)",
            new_status,
            machine.machine_code,
            sorted(VALID_MACHINE_STATUSES),
            extra={"machine_code": machine.machine_code, "status": new_status, "reason": "invalid_machine_status"},
        )
        raise ValueError(
            f"Trạng thái máy không hợp lệ: {new_status}. Phải là một trong: {', '.join(sorted(VALID_MACHINE_STATUSES))}"
        )

    current = old_status or getattr(machine, "status", None) or "IDLE"
    log.info(
        "Machine %s status changed: %s -> %s (reason: %s)",
        machine.machine_code,
        current,
        target,
        reason or "operator_update",
        extra={
            "machine_code": machine.machine_code,
            "old_status": current,
            "new_status": target,
            "reason": reason or "operator_update",
        },
    )
    if hasattr(machine, "status"):
        machine.status = target
        db.commit()
    return target


def assign_machine_to_step(db: Session, machine_id: int, route_step_id: int) -> RouteStepMachine:
    """Assign machine to a route step and log transition."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        log.warning(
            "Assign machine to step rejected: machine ID %s not found",
            machine_id,
            extra={"machine_id": machine_id, "route_step_id": route_step_id, "reason": "machine_not_found"},
        )
        raise ValueError(f"Không tìm thấy máy CNC với ID {machine_id}")

    existing = (
        db.query(RouteStepMachine)
        .filter(RouteStepMachine.machine_id == machine_id, RouteStepMachine.route_step_id == route_step_id)
        .first()
    )
    if existing:
        log.warning(
            "Assign machine to step rejected: machine %s already assigned to route step %s",
            machine.machine_code,
            route_step_id,
            extra={"machine_code": machine.machine_code, "route_step_id": route_step_id, "reason": "already_assigned"},
        )
        return existing

    link = RouteStepMachine(route_step_id=route_step_id, machine_id=machine_id)
    db.add(link)
    db.commit()
    log.info(
        "Machine %s assigned to route step %s",
        machine.machine_code,
        route_step_id,
        extra={"machine_code": machine.machine_code, "route_step_id": route_step_id},
    )
    return link


def unassign_machine_from_step(db: Session, machine_id: int, route_step_id: int) -> None:
    """Unassign machine from a route step and log transition."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    code = machine.machine_code if machine else f"ID={machine_id}"
    deleted = (
        db.query(RouteStepMachine)
        .filter(RouteStepMachine.machine_id == machine_id, RouteStepMachine.route_step_id == route_step_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted:
        log.info(
            "Machine %s unassigned from route step %s",
            code,
            route_step_id,
            extra={"machine_code": code, "route_step_id": route_step_id},
        )
    else:
        log.warning(
            "Unassign machine from step rejected: link not found between machine %s and step %s",
            code,
            route_step_id,
            extra={"machine_code": code, "route_step_id": route_step_id, "reason": "link_not_found"},
        )
