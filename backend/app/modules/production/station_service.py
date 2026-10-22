from sqlalchemy.orm import Session

from app.modules.production.production_models import Machine
from app.modules.production.station_schema import (
    StationCatalogResponse,
    StationCatalogItem,
    MachineCatalogGroup,
    MapAvailableNodeResponse,
    StationSlotCreateRequest,
    StationSlotUpdateRequest,
)
from app.modules.production.location_guard import (
    ensure_location_has_no_stock,
    find_map_node,
    release_location,
    resolve_warehouse_id,
)
from app.modules.warehouse.location_map.location_model import Location


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
                machine_code=loc.machine_code or "NOT_IN_CNC",
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
    wh_id = resolve_warehouse_id(db)

    node_lbl = (payload.node_label or "").strip()
    req_code = (payload.location_code or "").strip()
    custom_name = (payload.location_name or "").strip()

    loc = find_map_node(db, wh_id, node_lbl, req_code)
    if not loc:
        raise ValueError(f"Không tìm thấy node bản đồ '{node_lbl or req_code}' để gán trạm.")

    if loc.location_type != "UNASSIGNED" and loc.location_type != loc_type:
        raise ValueError(
            f"Node {loc.location_label or loc.location_code} đã được gán cho khu vực {loc.location_type} ({loc.location_name}). Không thể gán trùng!"
        )

    # Node tự do nhưng đang có xe/phôi nằm sẵn -> không cho dựng trạm đè lên
    if loc.location_type == "UNASSIGNED":
        ensure_location_has_no_stock(db, loc, "gán trạm mới")

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
    if loc.location_type == "UNASSIGNED":
        raise ValueError(f"Vị trí ID {location_id} chưa được gán trạm nào.")

    # 1. Đổi node bản đồ = chuyển trạm sang bản ghi Location (node vật lý) khác.
    #    KHÔNG sửa location_label của node cũ vì như vậy là làm sai dữ liệu bản đồ.
    new_ref = (payload.node_label or "").strip()
    if new_ref and new_ref not in {loc.location_code, loc.location_label}:
        target = find_map_node(db, loc.warehouse_id, new_ref)
        if not target:
            raise ValueError(f"Không tìm thấy node bản đồ '{new_ref}'.")
        if target.id != loc.id:
            if target.location_type != "UNASSIGNED":
                raise ValueError(
                    f"Node {target.location_label or target.location_code} đã được gán cho "
                    f"{target.location_type} ({target.location_name})."
                )
            ensure_location_has_no_stock(db, loc, "chuyển trạm khỏi vị trí cũ")
            ensure_location_has_no_stock(db, target, "chuyển trạm tới node mới")

            target.location_type = loc.location_type
            target.location_name = loc.location_name
            target.position_index = loc.position_index
            target.is_active = loc.is_active
            release_location(loc)
            loc = target


    if payload.location_name is not None:
        loc.location_name = payload.location_name.strip()
    if payload.position_index is not None:
        loc.position_index = payload.position_index
    # map_x/map_y là tọa độ vật lý của node (import từ map KUKA) -> không cho ghi đè từ form trạm.

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

    ensure_location_has_no_stock(db, loc, "giải phóng vị trí")
    release_location(loc)
    db.commit()
    return True


def get_available_map_nodes(
    db: Session,
    only_functional: bool = True,
    rack_only: bool = True,
) -> list[MapAvailableNodeResponse]:
    query = db.query(Location).filter(Location.is_active.is_(True))
    if rack_only:
        query = query.filter(Location.function_type == 2)
    elif only_functional:
        query = query.filter(Location.function_type.isnot(None))

    results: list[MapAvailableNodeResponse] = []
    for loc in query.all():
        node_lbl = str(loc.location_code )
        node_num = str(loc.location_label)
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
