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
    STATIC_MAP_DIR,
    _ensure_warehouse_and_zone,
)
from app.modules.warehouse.location_map.service.map_parser import (
    _is_kuka_floor_map,
    _read_map_raw_content,
    adapt_kuka_floor_map_to_canvas,
)

def resolve_map_zip_path(source: str) -> Path:
    path = Path(source)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path

def _load_compress_json(zip_path: Path) -> dict:
    if not zip_path.is_file():
        raise ValueError(f"Map file not found: {zip_path}")
    raw = zip_path.read_bytes()
    return _read_map_raw_content(raw)

def get_map_data(db: Session, warehouse_id: int) -> MapDataResponse:
    warehouse_map = (
        db.query(WarehouseMap)
        .filter(
            WarehouseMap.warehouse_id == warehouse_id,
            WarehouseMap.is_active.is_(True),
        )
        .first()
    )
    if warehouse_map is None:
        raise ValueError(f"No active map for warehouse_id={warehouse_id}")

    zip_path = resolve_map_zip_path(warehouse_map.source)
    data = _load_compress_json(zip_path)

    if _is_kuka_floor_map(data):
        return adapt_kuka_floor_map_to_canvas(data)

    # Chỉ trả field FE cần (MapData contract)
    try:
        return MapDataResponse(
            width=data["width"],
            height=data["height"],
            node_keys=data["nodeKeys"],
            line_keys=data["lineKeys"],
            node_arr=data["nodeArr"],
            line_arr=data["lineArr"],
            type=data.get("type"),
            x_attr_min=data.get("xAttrMin"),
            y_attr_min=data.get("yAttrMin"),
            map_format="legacy",
        )
    except KeyError as e:
        raise ValueError(f"Invalid compress.json: missing field {e.args[0]}") from e

def get_zone_map_layout(db: Session, zone_id: int) -> ZoneMapLayoutResponse:
    locations = (
        _location_query(db, include_inactive=False)
        .filter(Location.warehouse_id == zone_id)
        .order_by(Location.id)
        .all()
    )

    nodes = [
        ZoneMapLayoutNode(
            id=loc.id,
            location_code=loc.location_code,
            location_name=loc.location_name,
            bin_code=loc.bin_code,
            row=loc.row,
            column=loc.column,
            level=loc.level,
            map_x=loc.map_x,
            map_y=loc.map_y,
        )
        for loc in locations
    ]

    return ZoneMapLayoutResponse(
        zone_id=zone_id,
        warehouse_id=zone_id,
        nodes=nodes,
    )

def export_warehouse_map(db: Session, warehouse_id: int) -> tuple[bytes, str, str]:
    warehouse_map = db.query(WarehouseMap).filter(
        WarehouseMap.warehouse_id == warehouse_id,
        WarehouseMap.is_active.is_(True),
    ).first()
    if not warehouse_map:
        raise ValueError("Warehouse map not found")

    zip_path = resolve_map_zip_path(warehouse_map.source)

    if not zip_path.is_file():
        raise ValueError(f"Map file not found: {zip_path}")

    content = zip_path.read_bytes()
    if not content:
        raise ValueError("Map file is empty")

    is_json = zip_path.suffix.lower() == ".json" or content.strip().startswith(b"{")
    ext = ".json" if is_json else ".zip"
    media_type = "application/json" if is_json else "application/zip"
    filename = f"warehouse-map-{warehouse_id}{ext}"
    return content, filename, media_type
