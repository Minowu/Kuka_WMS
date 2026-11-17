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
    _location_query,
    location_ids_with_assigned_qr,
    overlay_status_with_assign_cache,
)

def list_locations_for_map(db: Session, warehouse_id: int) -> LocationsForMapResponse:
    if not db.query(Warehouse).filter(Warehouse.id == warehouse_id).first():
        raise ValueError(f"Warehouse id not found: {warehouse_id}")

    locations = (
        _location_query(db, include_inactive=False)
        .filter(Location.warehouse_id == warehouse_id)
        .order_by(Location.id)
        .all()
    )

    items: list[MapLocationItem] = []
    location_codes: list[str] = []
    assigned_ids = location_ids_with_assigned_qr()

    reserved_location_ids: set[int] = set()
    in_transit_pickup_ids: set[int] = set()
    pickup_task_map = {}
    dropoff_task_map = {}
    try:
        from app.modules.production.production_models import FleetTask, TransportRequest
        active_fleet_tasks = (
            db.query(FleetTask)
            .filter(FleetTask.status.in_(["created", "sent", "dispatched", "in_progress", "executing"]))
            .all()
        )
        pickup_task_map = {t.pickup_location_id: t for t in active_fleet_tasks if t.pickup_location_id}
        dropoff_task_map = {t.dropoff_location_id: t for t in active_fleet_tasks if t.dropoff_location_id}
        reserved_location_ids = set(dropoff_task_map.keys())
        in_transit_pickup_ids = set(pickup_task_map.keys())

        active_requests = (
            db.query(TransportRequest)
            .filter(TransportRequest.status.in_(["queued_for_cart", "in_progress"]))
            .all()
        )
        for r in active_requests:
            if r.destination_location_id:
                reserved_location_ids.add(r.destination_location_id)
    except Exception:
        pass 

    for loc in locations:
        stocks = [
            MapLocationStockItem(
                sku=stock.item.sku if stock.item else "",
                lot_number_from=getattr(stock, "lot_number_from", None),
                lot_number_to=getattr(stock, "lot_number_to", None),
                lot_number=format_lot_number_display(
                    getattr(stock, "lot_number_from", None),
                    getattr(stock, "lot_number_to", None),
                ),
                quantity=str(stock.quantity),
            )
            for stock in (loc.stocks or [])
            if stock.quantity is not None
            and stock.quantity > 0
            and (
                getattr(stock, "stock_level", None) is None or getattr(stock, "stock_level", 1) <= 1
            )
        ]
        active_stock = next(
            (s for s in (loc.stocks or []) if s.quantity is not None and s.quantity > 0),
            next((s for s in (loc.stocks or []) if s.container_code), None)
        )
        active_container = active_stock.container_code if active_stock else None
        model_name = active_stock.item.sku if (active_stock and active_stock.item) else None
        current_stage = active_stock.current_stage_level if active_stock else None

        transit_target = None
        if loc.id in dropoff_task_map:
            status = "reserved"
            task = dropoff_task_map[loc.id]
            src_name = task.pickup_location.location_name if task.pickup_location else "trạm nguồn"
            transit_target = f"Từ {src_name}"
        elif loc.id in pickup_task_map or (active_stock and getattr(active_stock, "is_locked", False)):
            status = "in_transit"
            task = pickup_task_map.get(loc.id)
            dst_name = task.dropoff_location.location_name if (task and task.dropoff_location) else "trạm đích"
            transit_target = f"Đến {dst_name}"
        elif stocks or active_container:
            status = "has_stock"
        else:
            status = getattr(loc, "status", "empty") or "empty"

        status = overlay_status_with_assign_cache(status, loc.id, assigned_ids)
        if stocks or active_container or loc.id in assigned_ids or status in ("reserved", "in_transit", "has_stock"):
            location_codes.append(loc.location_code)
            if loc.location_label and loc.location_label not in location_codes:
                location_codes.append(loc.location_label)
            if loc.location_name and loc.location_name not in location_codes:
                location_codes.append(loc.location_name)
        items.append(
            MapLocationItem(
                id=loc.id,
                location_code=loc.location_code,
                location_name=loc.location_name,
                location_label=getattr(loc, "location_label", None),
                location_type=getattr(loc, "location_type", None),
                container_code=active_container,
                model_name=model_name,
                current_stage_level=current_stage,
                transit_target_name=transit_target,
                machine_code=loc.machine.machine_code if loc.machine else None,
                position_index=getattr(loc, "position_index", None),
                row=getattr(loc, "row", None),
                column=getattr(loc, "column", None),
                level=getattr(loc, "level", None),
                map_x=loc.map_x,
                map_y=loc.map_y,
                status=status,
                item_stock=stocks,
            )
        )

    return LocationsForMapResponse(
        warehouse_id=warehouse_id,
        location_codes=location_codes,
        locations=items,
    )

def list_locations_for_zone_map(db: Session, zone_id: int) -> LocationsForMapResponse:
    """Fallback to warehouse map after Zone table removal."""
    return list_locations_for_map(db, zone_id)
