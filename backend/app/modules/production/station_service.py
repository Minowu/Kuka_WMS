from typing import Optional
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
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse


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
    wh = db.query(Warehouse).first()
    wh_id = wh.id if wh else 1

    node_lbl = (payload.node_label or "").strip()
    req_code = (payload.location_code or "").strip()
    custom_name = (payload.location_name or "").strip()

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
