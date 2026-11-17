"""Location service."""

from typing import Optional
from app.core.cache import cache_scan_keys, cache_set, get_redis

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from app.core.config import settings
from app.core.warehouse_mode import is_manual_warehouse
from app.modules.warehouse.lot_number_utils import format_lot_number_display

from app.modules.warehouse.location_map.location_model import Location, WarehouseMap
from decimal import Decimal

from app.modules.warehouse.location_map.location_schema import (
    LocationCreate,
    LocationDetailResponse,
    LocationDetailStockItem,
    LocationDetailSummary,
    LocationListResponse,
    LocationResponse,
    LocationUpdate,
    LocationsForMapResponse,
    MapCreate,
    MapDataResponse,
    MapLocationItem,
    MapLocationStockItem,
    ZoneMapLayoutNode,
    ZoneMapLayoutResponse,
)
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse
from app.modules.warehouse.item_stock.item_stock_model import (
    ItemStock,
    countable_stock_level_criterion,
)
from app.modules.production.production_models import (
    FleetTask,
    Machine,
    ProductionRecord,
    TransportRequest,
    UserLocation,
)
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
import base64
import math
import re
import zipfile
from dataclasses import dataclass
from typing import Optional
import io
import json

BACKEND_ROOT = Path(__file__).resolve().parents[4]  # → backend/
STATIC_MAP_DIR = BACKEND_ROOT / "static" / "warehouse_maps"
SHELF_NODE_NAME_PATTERN = re.compile(
    r"^R(?P<row>\d+)[_-]C(?P<column>\d+)[_-]L(?P<level>\d+)[_-]B(?P<bin>.+)$",
    re.IGNORECASE,
)
# A node name made only of digits is the map editor's default (it mirrors the node
# number), so it carries no identity that survives a re-export.
UNLABELLED_NODE_NAME_PATTERN = re.compile(r"^\d+$")

NODE_NAME_MAX_LENGTH = 50

# Every column in the schema that points at location.id. Used to count references
# before retiring a location and to move them during a remap.
LOCATION_FK_COLUMNS: tuple[tuple[type, str], ...] = (
    (ItemStock, "location_id"),
    (ItemStock, "destination_location_id"),
    (TransportRequest, "source_location_id"),
    (TransportRequest, "destination_location_id"),
    (FleetTask, "pickup_location_id"),
    (FleetTask, "dropoff_location_id"),
    (ProductionRecord, "location_id"),
    (UserLocation, "location_id"),
)



from app.modules.warehouse.location_map.service.common import (
    _assigned_stocks_for_location,
    _ensure_warehouse_and_zone,
    _location_query,
    _resolve_or_create_machine,
    location_ids_with_assigned_qr,
)

def list_locations(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    warehouse_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    q: Optional[str] = None,
    include_inactive: bool = False,
) -> LocationListResponse:
    query = _location_query(db, include_inactive=include_inactive)
    if warehouse_id is not None:
        query = query.filter(Location.warehouse_id == warehouse_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Location.location_code.ilike(like))
            | (Location.location_name.ilike(like))
            | (Location.bin_code.ilike(like))
        )
    total = query.count()
    items = (
        query.order_by(Location.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return LocationListResponse(
        items=[LocationResponse.model_validate(loc) for loc in items],
        total=total,
        page=page,
        page_size=page_size,
    )

def get_location_by_id(
    db: Session, location_id: int, *, include_inactive: bool = False
) -> Optional[Location]:
    return (
        _location_query(db, include_inactive=include_inactive)
        .filter(Location.id == location_id)
        .first()
    )

def get_location_detail(db: Session, location_id: int) -> LocationDetailResponse:
    location = get_location_by_id(db, location_id, include_inactive=True)
    if not location:
        raise ValueError("Location not found")

    item_stock: list[LocationDetailStockItem] = []
    total_qty = Decimal("0")

    for stock in location.stocks or []:
        if not stock.is_active:
            continue
        stock_level = getattr(stock, "stock_level", None)
        if stock_level is not None and stock_level > 1:
            continue
        qty = stock.quantity if stock.quantity is not None else Decimal("0")
        if qty <= 0:
            continue
        total_qty += qty
        lot_from = getattr(stock, "lot_number_from", None)
        lot_to = getattr(stock, "lot_number_to", None)
        item_stock.append(
            LocationDetailStockItem(
                id=stock.id,
                item_id=stock.item_id,
                sku=stock.item.sku if stock.item else "",
                lot_number_from=lot_from,
                lot_number_to=lot_to,
                lot_number=format_lot_number_display(lot_from, lot_to),
                expiry_date=getattr(stock, "expiry_date", None),
                quantity=str(qty),
                status=stock.status,
            )
        )

    for assigned in _assigned_stocks_for_location(location_id):
        qty = Decimal(str(assigned.get("quantity") or 0))
        total_qty += qty
        lot = assigned.get("lot_number")
        qr_id = int(assigned["qr_code_id"])
        item_stock.append(
            LocationDetailStockItem(
                # tránh trùng id stock DB; drawer dùng làm React key
                id=-qr_id,
                item_id=int(assigned["item_id"]),
                sku=assigned.get("item_sku") or "",
                lot_number_from=lot,
                lot_number_to=lot,
                lot_number=lot,
                expiry_date=None,
                quantity=str(qty),
                status="assigned",  # hoặc "staged"
            )
        )

    loc_resp = LocationResponse.model_validate(location)
    if loc_resp.status == "empty" and any(s.status == "assigned" for s in item_stock):
        loc_resp = loc_resp.model_copy(update={"status": "has_stock"})

    active_stock = next(
        (s for s in (location.stocks or []) if s.quantity is not None and s.quantity > 0),
        next((s for s in (location.stocks or []) if s.container_code), None)
    )
    container_code = active_stock.container_code if active_stock else None
    model_name = active_stock.item.sku if (active_stock and active_stock.item) else None
    current_stage = active_stock.current_stage_level if active_stock else None

    stage_name = None
    if active_stock:
        if location.location_type == "RAW_MATERIAL" or current_stage == 0:
            stage_name = "Phôi thô chờ gia công"
        elif location.location_type == "WASHING_SLOT":
            stage_name = "Chờ tẩy rửa thành phẩm"
        elif location.location_type == "EMPTY_CART_BUFFER":
            stage_name = "Xe rỗng sẵn sàng cấp phôi"
        else:
            # Tra cứu tên công đoạn thực tế từ RouteStep trong DB của Model này
            try:
                from app.modules.production.production_models import ProductionRoute, RouteStep
                step = (
                    db.query(RouteStep)
                    .join(ProductionRoute, ProductionRoute.id == RouteStep.route_id)
                    .filter(
                        ProductionRoute.item_id == active_stock.item_id,
                        ProductionRoute.is_active.is_(True),
                        RouteStep.stage_level == current_stage,
                    )
                    .order_by(ProductionRoute.version.desc())
                    .first()
                )
                if step and step.step_name:
                    stage_name = step.step_name
                else:
                    stage_name = f"Công đoạn {current_stage}"
            except Exception:
                stage_name = f"Công đoạn {current_stage}"

    machine_code = location.machine.machine_code if location.machine else None
    machine_name = location.machine.machine_name if location.machine else None
    position_name = f"Vị trí POS{location.position_index}" if location.position_index else None

    transit_info = None
    try:
        from app.modules.production.production_models import FleetTask
        active_task = (
            db.query(FleetTask)
            .filter(
                (FleetTask.pickup_location_id == location_id) | (FleetTask.dropoff_location_id == location_id),
                FleetTask.status.in_(["created", "sent", "dispatched", "in_progress", "executing"])
            )
            .first()
        )
        if active_task:
            if active_task.pickup_location_id == location_id:
                dest = active_task.dropoff_location.location_name if active_task.dropoff_location else "trạm đích"
                transit_info = f"Đang chuyển đến {dest}"
            elif active_task.dropoff_location_id == location_id:
                src = active_task.pickup_location.location_name if active_task.pickup_location else "trạm nguồn"
                transit_info = f"Đang chờ xe từ {src}"
    except Exception:
        pass

    return LocationDetailResponse(
        location=loc_resp,
        item_stock=item_stock,
        summary=LocationDetailSummary(
            item_stock_count=len(item_stock),
            total_quantity=str(total_qty),
        ),
        container_code=container_code,
        model_name=model_name,
        quantity=str(total_qty) if total_qty > 0 else (str(active_stock.quantity) if active_stock else None),
        current_stage_level=current_stage,
        stage_name=stage_name,
        machine_code=machine_code,
        machine_name=machine_name,
        position_name=position_name,
        transit_info=transit_info,
    )

def upsert_location(db: Session, body: LocationCreate) -> Location:
    _ensure_warehouse_and_zone(db, body.warehouse_id)

    # bin_code is the physical identity; location_code is only the current map node.
    existing = None
    if body.bin_code:
        existing = (
            db.query(Location)
            .filter(
                Location.warehouse_id == body.warehouse_id,
                Location.bin_code == body.bin_code.strip(),
            )
            .first()
        )
    if existing is None:
        existing = (
            db.query(Location)
            .filter(
                Location.warehouse_id == body.warehouse_id,
                Location.location_code == body.location_code,
            )
            .first()
        )

    if existing:
        return update_location(db, existing.id, LocationUpdate(
            location_code=body.location_code.strip(),
            location_name=body.location_name.strip(),
            bin_code=body.bin_code.strip() if body.bin_code else None,
            row=body.row,
            column=body.column,
            level=body.level,
            node_name=body.node_name,
            warehouse_id=body.warehouse_id,
            is_active=True,
        ))
    else:
        location = Location(
            location_code=body.location_code.strip(),
            location_name=body.location_name.strip(),
            bin_code=body.bin_code.strip() if body.bin_code else None,
            row=body.row,
            column=body.column,
            level=body.level,
            node_name=body.node_name,
            warehouse_id=body.warehouse_id,
            is_active=True,
        )
        db.add(location)
        db.flush()
        return location

def update_location(
    db: Session, location_id: int, body: LocationUpdate
) -> Optional[Location]:
    location = get_location_by_id(db, location_id, include_inactive=True)
    if not location:
        return None
    data = body.model_dump(exclude_unset=True)
    warehouse_id = data.get("warehouse_id", location.warehouse_id)
    if "warehouse_id" in data:
        _ensure_warehouse_and_zone(db, warehouse_id)
        location.warehouse_id = warehouse_id
    if "location_code" in data:
        existing = (
            db.query(Location)
            .filter(
                Location.warehouse_id == warehouse_id,
                Location.location_code == data["location_code"],
                Location.id != location_id,
            )
            .first()
        )
        if existing:
            raise ValueError("Location code already exists in this warehouse")
        location.location_code = data["location_code"].strip()
    # location_name is only a display label, so duplicates are allowed. bin_code is
    # the identity and stays unique per warehouse.
    if data.get("bin_code"):
        existing = (
            db.query(Location)
            .filter(
                Location.warehouse_id == warehouse_id,
                Location.bin_code == data["bin_code"],
                Location.id != location_id,
            )
            .first()
        )
        if existing:
            raise ValueError("Bin code already exists in this warehouse")
        location.bin_code = data["bin_code"].strip()
    if "location_name" in data:
        location.location_name = data["location_name"].strip()
    for field in (
        "row",
        "column",
        "level",
        "node_name",
        "is_active",
        "map_x",
        "map_y",
        "location_type",
        "machine_code",
        "position_index",
        "node_label",
    ):
        if field in data:
            setattr(location, field, data[field])

    if location.machine_code:
        machine = _resolve_or_create_machine(
            db,
            location.machine_code,
            warehouse_id,
        )
        location.machine_id = machine.id if machine else None
    elif "machine_code" in data and not data.get("machine_code"):
        location.machine_id = None

    db.flush()
    return location

def delete_location(db: Session, location_id: int) -> bool:
    location = get_location_by_id(db, location_id)
    if not location:
        return False
    if (
        db.query(ItemStock)
        .filter(
            ItemStock.location_id == location_id,
            ItemStock.is_active.is_(True),
        )
        .first()
    ):
        raise ValueError("Cannot delete location: item stocks still exist")
    if (
        db.query(FleetTask)
        .filter(
            ((FleetTask.pickup_location_id == location_id) | (FleetTask.dropoff_location_id == location_id)),
            FleetTask.status.in_(["created", "sent", "in_progress"]),
        )
        .first()
    ):
        raise ValueError("Cannot delete location: active fleet tasks still exist")
    location.is_active = False
    db.commit()
    return True

def get_locations_by_logic(db: Session, warehouse_id: int, type: str) -> list[Location]:
    type_map = {
        "inbound_buffer": "RAW_MATERIAL",
        "raw_material": "RAW_MATERIAL",
        "qc_buffer": "WASHING_SLOT",
        "washing_slot": "WASHING_SLOT",
        "outbound_buffer": "EMPTY_CART_BUFFER",
        "empty_cart_buffer": "EMPTY_CART_BUFFER",
        "storage_area": "CNC_SLOT",
        "cnc_slot": "CNC_SLOT",
    }
    loc_type = type_map.get(type)
    if not loc_type:
        raise ValueError(f"Unsupported location type: {type}")
    return (
        db.query(Location)
        .filter(
            Location.warehouse_id == warehouse_id,
            Location.is_active.is_(True),
            Location.location_type == loc_type,
        )
        .order_by(Location.location_code)
        .all()
    )

