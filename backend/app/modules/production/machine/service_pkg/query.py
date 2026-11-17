from typing import Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.modules.production.production_models import Machine, RouteStepMachine
from app.modules.production.machine.schema import (
    MAX_MACHINE_SLOTS,
    AvailableMachineResponse,
    MachineCreateRequest,
    MachineUpdateRequest,
    MachineSlotCreate,
    MachineSlotInfo,
)
from app.modules.production.dispatch.location_guard import (
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


